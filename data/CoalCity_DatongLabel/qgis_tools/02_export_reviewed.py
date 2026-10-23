# -*- coding: utf-8 -*-
"""Run only after independently reviewing and editing every polygon in QGIS.
This exporter checks coverage/overlap/encoding, NOT semantic correctness.
"""
from pathlib import Path
import datetime,json
import numpy as np
from osgeo import gdal,ogr,osr
from qgis.core import QgsProject

OUTPUT_ROOT=Path(r'D:\CoalCity\output')
def export_reviewed():
    gdal.UseExceptions()
    project=QgsProject.instance()
    if project.isDirty() or any(l.isEditable() for l in project.mapLayers().values() if hasattr(l,'isEditable')):
        raise RuntimeError('请先保存所有图层编辑，退出编辑模式，并保存QGIS工程。')
    run=Path(project.fileName()).parent
    gp=run/'CN01_review.gpkg';ref=run/'CN01_CUFR_mask.tif'
    if not gp.exists() or not ref.exists():raise RuntimeError('请先打开01脚本生成的CN01_review.qgz。')
    vd=ogr.Open(str(gp));layer=vd.GetLayerByName('label_polygons')
    problems=[];valid_ids=set(range(14))|{255};seen=0
    for f in layer:
        c=f.GetField('class_id');g=f.GetGeometryRef();fid=f.GetFID();seen+=1
        if f.GetField('verified')!=1:problems.append((fid,'未复核'))
        if c not in valid_ids:problems.append((fid,'非法/待判定类别'))
        if g is None or g.IsEmpty() or not g.IsValid():problems.append((fid,'无效几何'))
        if c in [8,9,10,11,12,13,255] and not (f.GetField('evidence') or '').strip():problems.append((fid,'需填写功能证据/其他类别内容/Ignore原因'))
    if not seen:raise RuntimeError('标注图层为空。')
    if problems:
        print('前20项问题：',problems[:20]);raise RuntimeError('还有%d项问题；未导出正式文件。'%len(problems))
    base=gdal.Open(str(ref));w,h=base.RasterXSize,base.RasterYSize;inside=base.ReadAsArray().astype(bool)
    s=osr.SpatialReference();s.ImportFromWkt(base.GetProjection())
    if not layer.GetSpatialRef().IsSame(s):raise RuntimeError('标注矢量与参考栅格坐标系不一致。')
    def mem(dtype):
        d=gdal.GetDriverByName('MEM').Create('',w,h,1,dtype);d.SetGeoTransform(base.GetGeoTransform());d.SetProjection(base.GetProjection());d.GetRasterBand(1).Fill(0);return d
    # Count pixel-center coverage, preventing rasterization order from hiding overlaps.
    coverage=mem(gdal.GDT_UInt16);layer.ResetReading();gdal.RasterizeLayer(coverage,[1],layer,burn_values=[1],options=['MERGE_ALG=ADD'])
    n=coverage.ReadAsArray();missing=int(np.count_nonzero(inside&(n==0)));overlap=int(np.count_nonzero(inside&(n>1)))
    if missing or overlap:raise RuntimeError('CUFR内漏标%d像素、重叠%d像素；先修正后再导出。'%(missing,overlap))
    # Also catch subpixel overlaps/invalid boundaries that pixel-center coverage can miss.
    vl=next((l for l in project.mapLayers().values() if hasattr(l,'getFeatures') and Path(l.source().split('|')[0]).resolve()==gp.resolve()),None)
    if vl is None:raise RuntimeError('请在工程中加载label_polygons图层再运行。')
    from qgis.core import QgsSpatialIndex,QgsGeometry
    index=QgsSpatialIndex(vl.getFeatures());geoms={f.id():QgsGeometry(f.geometry()) for f in vl.getFeatures()}
    for fid,g in geoms.items():
        for other in index.intersects(g.boundingBox()):
            if other<=fid:continue
            if g.intersection(geoms[other]).area()>1.0:raise RuntimeError('矢量存在超过1平方米的重叠：%s、%s'%(fid,other))
    # 254 is used as an internal sentinel and must be completely gone within CUFR.
    out=mem(gdal.GDT_Byte);out.GetRasterBand(1).Fill(254);layer.ResetReading();gdal.RasterizeLayer(out,[1],layer,options=['ATTRIBUTE=class_id'])
    a=out.ReadAsArray();a[~inside]=255
    if not set(np.unique(a[inside])).issubset(valid_ids):raise RuntimeError('最终像素编码检查失败。')
    finaldir=run/('reviewed_export_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));finaldir.mkdir()
    path=finaldir/'CoalCity40_CN01_label.tif'
    d=gdal.GetDriverByName('GTiff').Create(str(path),w,h,1,gdal.GDT_Byte,options=['COMPRESS=DEFLATE','TILED=YES'])
    d.SetGeoTransform(base.GetGeoTransform());d.SetProjection(base.GetProjection());d.GetRasterBand(1).SetNoDataValue(255);d.GetRasterBand(1).WriteArray(a);d=None
    check=gdal.Open(str(path));assert np.array_equal(check.ReadAsArray(),a) and check.GetGeoTransform()==base.GetGeoTransform()
    audit={'status':'EXPORTED_FROM_USER_VERIFIED_POLYGONS','pixels_inside':int(inside.sum()),'missing_pixels':missing,'overlap_pixels':overlap,'all_polygons_marked_verified_by_user':True,'semantic_accuracy_independently_measured':False,'boundary_accuracy_independently_measured':False,'MMU_and_road_width_require_visual_QC':True,'source_geopackage':str(gp),'output':str(path)}
    (finaldir/'export_QC.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print('已从用户确认的多边形导出：',path)
    print('技术QC通过不代表语义或边界准确率已经实测。请同时保存GPKG、工程和证据日志。')

export_reviewed()
