# -*- coding: utf-8 -*-
"""Run inside QGIS Python Console. No pip installation needed.
Rule-based candidates, NOT trained-model predictions or ground truth.
"""
from pathlib import Path
import json, datetime, traceback
import numpy as np

INPUT_ROOT = Path(r'D:\CoalCity\input')
OUTPUT_ROOT = Path(r'D:\CoalCity\output')
REFLECTANCE_DIVISOR = 10000.0  # Sentinel-2 integer reflectance; use 1.0 for 0..1 rasters.
NAMES = {0:'高密度建成区候选',1:'低密度建成区候选',2:'农田候选',3:'林木/高密度植被候选',4:'草地/稀疏植被候选',5:'裸地候选',6:'普通水体候选',7:'道路',8:'活跃采掘区',9:'排土/废弃物堆场',10:'沉陷水体',11:'煤炭加工/电力设施',12:'煤炭物流',13:'其他',254:'无法自动建议/待判定',255:'云影等Ignore候选'}
COLORS={0:'#d73027',1:'#fc8d59',2:'#e6c229',3:'#16713b',4:'#8ecb66',5:'#b59c78',6:'#3288bd',7:'#dddddd',8:'#a50026',9:'#70453a',10:'#5e4fa2',11:'#f46d43',12:'#8b4b9f',13:'#aaaaaa',254:'#ff00ff',255:'#555555'}

def box_mean(a, radius):
    """Local context only; never reproject or resize the label grid."""
    if radius==0:return a.astype('float32')
    p=np.pad(a.astype('float32'),radius,mode='edge')
    v=np.pad(p,((1,0),(1,0)),mode='constant').cumsum(0,dtype='float64').cumsum(1)
    k=2*radius+1
    return ((v[k:,k:]-v[:-k,k:]-v[k:,:-k]+v[:-k,:-k])/(k*k)).astype('float32')

def candidates(red,green,blue,nir,swir,scl,inside):
    """Untuned spectral/spatial heuristics; every suggested class requires review."""
    good=np.isfinite(red+green+blue+nir+swir)&((red+green+blue+nir+swir)>0)
    ndvi=(nir-red)/(nir+red+1e-8)
    ndwi=(green-nir)/(green+nir+1e-8)
    ndbi=(swir-nir)/(swir+nir+1e-8)
    cloud=np.isin(scl,[3,8,9,10])&inside
    usable=good&inside&~cloud
    # SCL is used only for obstruction candidates, never as semantic ground truth.
    water=(ndwi>.12)&(ndvi<.18)&(nir<.18)
    built=(ndbi>.02)&(ndvi<.25)&((red+green+blue)/3>.07)&~water&usable
    density=box_mean(built,10)  # 21x21-pixel context; not a calibrated density measure.
    ndmean=box_mean(ndvi,2)
    texture=np.sqrt(np.maximum(box_mean(ndvi*ndvi,2)-ndmean*ndmean,0))
    out=np.full(red.shape,254,np.uint8)
    out[usable&water]=6
    out[usable&~water&(ndvi>=.22)]=4
    # Spectral similarity cannot establish crop/tree identity; flag for priority review.
    farm=usable&~water&(ndvi>=.35)&(texture<.075)
    out[farm]=2
    out[usable&~water&(ndvi>=.60)&(texture>=.075)]=3
    out[usable&~water&(ndvi<.22)&~built]=5
    out[usable&built&(density<.5)]=1
    out[usable&built&(density>=.5)]=0
    out[cloud]=255
    out[~inside]=255
    # Bit mask: 1=requires review (all CUFR),2=cloud/shadow,4=vegetation ambiguity,
    # 8=built/bare ambiguity,16=water-vs-shadow or type,32=coal facility vicinity,
    # 64=no spectral suggestion,128=class transition (added after sieve).
    reason=np.zeros(red.shape,np.uint8);reason[inside]=1
    reason[cloud]|=2
    reason[usable&(ndvi>=.22)]|=4
    reason[usable&((ndvi<.3)|(np.abs(ndbi)<.08))&~water]|=8
    reason[usable&water]|=16
    reason[inside&(out==254)]|=64
    return out,reason

def main(input_root=INPUT_ROOT,output_root=OUTPUT_ROOT):
    from osgeo import gdal,ogr,osr
    from qgis.core import (QgsProject,QgsRasterLayer,QgsVectorLayer,QgsCoordinateReferenceSystem,
        QgsPalettedRasterRenderer,QgsMultiBandColorRenderer,QgsContrastEnhancement,
        QgsCategorizedSymbolRenderer,QgsRendererCategory,QgsFillSymbol,QgsMarkerSymbol)
    from qgis.PyQt.QtGui import QColor
    from qgis.PyQt.QtCore import QCoreApplication
    gdal.UseExceptions()
    root=Path(input_root)
    hits=list(root.rglob('CN01_B04.tif')) if root.exists() else []
    if len(hits)!=1:raise RuntimeError('应找到且只找到一份CN01_B04.tif，实际%d份；检查INPUT_ROOT。'%len(hits))
    src=hits[0].parent
    paths={k:src/('CN01_'+k+'.tif') for k in ['B02','B03','B04','B08','B11','SCL']}
    for f in paths.values():
        if not f.exists():raise FileNotFoundError(str(f))
    boundary=src/'CN01_CUFR_circle_UTM.geojson'
    if not boundary.exists():raise FileNotFoundError(str(boundary))
    ds={k:gdal.Open(str(f)) for k,f in paths.items()}
    base=ds['B04'];w,h=base.RasterXSize,base.RasterYSize;gt=base.GetGeoTransform();wkt=base.GetProjection()
    srs=osr.SpatialReference();srs.ImportFromWkt(wkt)
    if not srs.IsProjected() or abs(srs.GetLinearUnits()-1)>1e-8:raise RuntimeError('需要米制投影坐标系。')
    if not np.allclose([gt[1],gt[2],gt[4],gt[5]],[10,0,0,-10],atol=1e-8):raise RuntimeError('需要北向上10m网格。')
    for k,d in ds.items():
        q=osr.SpatialReference();q.ImportFromWkt(d.GetProjection())
        if (d.RasterXSize,d.RasterYSize)!=(w,h) or not np.allclose(d.GetGeoTransform(),gt,atol=1e-8,rtol=0) or not q.IsSame(srs):
            raise RuntimeError(k+'网格不一致；脚本不会静默重采样。')
    # Refuse running into an unsaved current project; save outputs as a separate project.
    current=QgsProject.instance()
    if current.isDirty():raise RuntimeError('当前QGIS工程有未保存修改，请先保存工程再运行。')
    run=Path(output_root)/('CN01_prelabel_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    run.mkdir(parents=True,exist_ok=False)
    def mem(dtype=gdal.GDT_Byte):
        d=gdal.GetDriverByName('MEM').Create('',w,h,1,dtype);d.SetGeoTransform(gt);d.SetProjection(wkt);return d
    def save(name,a,nodata=255):
        d=gdal.GetDriverByName('GTiff').Create(str(run/name),w,h,1,gdal.GDT_Byte,options=['COMPRESS=DEFLATE','TILED=YES','BIGTIFF=IF_SAFER'])
        d.SetGeoTransform(gt);d.SetProjection(wkt);d.GetRasterBand(1).SetNoDataValue(nodata);d.GetRasterBand(1).WriteArray(a)
        d.SetMetadata({'STATUS':'UNREVIEWED_CANDIDATES_NOT_GROUND_TRUTH','PENDING_CODE':'254'});d.FlushCache();return d
    bsrc=ogr.Open(str(boundary));bl=bsrc.GetLayer();bcrs=bl.GetSpatialRef()
    if bcrs is None or not bcrs.IsSame(srs):raise RuntimeError('CUFR边界投影缺失或与影像不一致。')
    bm=mem();bm.GetRasterBand(1).Fill(0);gdal.RasterizeLayer(bm,[1],bl,burn_values=[1]);inside=bm.ReadAsArray().astype(bool)
    if not inside.any():raise RuntimeError('CUFR与影像不相交。')
    print('输入:',src,' 网格:',w,h,' 输出:',run)
    result=np.full((h,w),255,np.uint8);reasons=np.zeros((h,w),np.uint8)
    # Strip processing limits memory, with halos for a seamless 21x21 context.
    for y in range(0,h,256):
        n=min(256,h-y);y0=max(0,y-12);y1=min(h,y+n+12);cut=slice(y-y0,y-y0+n)
        a={k:d.GetRasterBand(1).ReadAsArray(0,y0,w,y1-y0).astype('float32')/REFLECTANCE_DIVISOR for k,d in ds.items() if k!='SCL'}
        scl=ds['SCL'].ReadAsArray(0,y0,w,y1-y0)
        c,r=candidates(a['B04'],a['B03'],a['B02'],a['B08'],a['B11'],scl,inside[y0:y1])
        result[y:y+n]=c[cut];reasons[y:y+n]=r[cut]
        print('光谱候选进度 %d%%'%round(100*(y+n)/h));QCoreApplication.processEvents()
    # Remove small ordinary patches only; restore high-priority water and obstruction/pending.
    raw=mem();raw.GetRasterBand(1).WriteArray(result)
    sm=mem();valid=mem();valid.GetRasterBand(1).WriteArray((inside&(result<14)).astype('uint8'))
    gdal.SieveFilter(raw.GetRasterBand(1),valid.GetRasterBand(1),sm.GetRasterBand(1),4,4)
    filtered=sm.ReadAsArray();keep=(result==6)|(result>=254);filtered[keep]=result[keep];result=filtered
    # Facility locations are review cues ONLY; they never generate coal-function labels.
    facilities=[('中煤塔山',113.08686,39.950913),('同忻',113.103349,40.013182),('云冈矿',113.07991,40.11977),('晋华宫',113.15252,40.09963),('煤峪口',113.13136,40.03058),('忻州窑_车站参照',113.11760,40.04671),('白洞井_车站参照',113.05566,40.00086),('大同第二发电厂',113.29417,40.02816)]
    wgs=osr.SpatialReference();wgs.ImportFromEPSG(4326)
    if hasattr(wgs,'SetAxisMappingStrategy'):wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct=osr.CoordinateTransformation(wgs,srs)
    yy,xx=np.ogrid[:h,:w];px=gt[0]+(xx+.5)*10;py=gt[3]-(yy+.5)*10
    fac_geo=[]
    for name,lon,lat in facilities:
        x,y,_=ct.TransformPoint(lon,lat);near=((px-x)**2+(py-y)**2<=1000**2)&inside;reasons[near]|=32
        fac_geo.append({'type':'Feature','geometry':{'type':'Point','coordinates':[lon,lat]},'properties':{'name':name,'purpose':'review cue only; NOT a facility boundary','source':'上传大同设施调研，未独立核验','review_radius_m':1000}})
    (run/'facility_review_points.geojson').write_text(json.dumps({'type':'FeatureCollection','features':fac_geo},ensure_ascii=False),encoding='utf-8')
    # Class-transition edges for priority review; no claimed probability/confidence.
    edge=np.zeros((h,w),bool);edge[1:]|=result[1:]!=result[:-1];edge[:,1:]|=result[:,1:]!=result[:,:-1]
    reasons[edge&inside]|=128
    candidate=save('CN01_PRELABEL_NOT_FINAL.tif',result)
    rd=save('CN01_review_reasons.tif',reasons,0);bd=save('CN01_CUFR_mask.tif',inside.astype('uint8'),0)
    # RGB from georeferenced source bands; never rely on unreferenced PNG for final geometry.
    vrt=gdal.BuildVRT(str(run/'CN01_RGB.vrt'),[str(paths[k]) for k in ['B04','B03','B02']],separate=True);vrt=None
    gp=str(run/'CN01_review.gpkg');vd=ogr.GetDriverByName('GPKG').CreateDataSource(gp)
    layer=vd.CreateLayer('label_polygons',srs,ogr.wkbPolygon)
    for name,typ in [('class_id',ogr.OFTInteger),('verified',ogr.OFTInteger),('priority',ogr.OFTInteger),('note',ogr.OFTString),('evidence',ogr.OFTString)]:layer.CreateField(ogr.FieldDefn(name,typ))
    # Every inside pixel has an explicit polygon, including 254 and Ignore candidates.
    print('正在矢量化，可能需要数分钟，请勿关闭QGIS。')
    gdal.Polygonize(candidate.GetRasterBand(1),bd.GetRasterBand(1),layer,0,[])
    layer.StartTransaction()
    count=0
    for feat in layer:
        c=feat.GetField('class_id');feat.SetField('verified',0);feat.SetField('priority',2 if c in [254,255,2,3,0,1] else 1)
        feat.SetField('note','自动规则候选；未人工复核；不是最终真值');feat.SetField('evidence','');layer.SetFeature(feat);count+=1
    layer.CommitTransaction();vd=None
    values,counts=np.unique(result[inside],return_counts=True)
    summary={'status':'UNREVIEWED_RULE_BASED_PRELABEL','input':str(src),'output':str(run),'shape':[h,w],'geotransform':list(gt),'crs':wkt,'class_counts_inside':{str(int(v)):int(n) for v,n in zip(values,counts)},'polygons':count,'verified_pixels':0,'all_CUFR_requires_review':True,'coal_function_classes_auto_assigned':False,'road_class_auto_assigned':False,'parameters':{'reflectance_divisor':REFLECTANCE_DIVISOR,'ndvi_vegetation':.22,'ndvi_crop_candidate':.35,'ndvi_dense_candidate':.60,'ndwi_water':.12,'ndbi_built':.02,'context_window':21,'MMU_sieve_pixels':4},'limitations':['规则未经标注样本校准；类别准确率未知','农田与林草、裸地与建成区不能由指数可靠区分','道路及8—13类需要人工补画/更正','所有verified=0；全域生成不等于全域完成','设施1km邻域仅用于排查，绝非语义边界','SCL云影/薄云是待复核候选，不是已经确认的Ignore']}
    (run/'run_report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    candidate=None;rd=None;bd=None
    # Build a separate project, never overwrite the user's existing project.
    project=QgsProject();project.setCrs(QgsCoordinateReferenceSystem(wkt))
    rgb=QgsRasterLayer(str(run/'CN01_RGB.vrt'),'S2真彩色_地理参考底图')
    if not rgb.isValid():raise RuntimeError('RGB底图加载失败，预标注文件已写入。')
    renderer=QgsMultiBandColorRenderer(rgb.dataProvider(),1,2,3)
    for band,setter in [(1,renderer.setRedContrastEnhancement),(2,renderer.setGreenContrastEnhancement),(3,renderer.setBlueContrastEnhancement)]:
        enh=QgsContrastEnhancement(rgb.dataProvider().dataType(band));enh.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum);enh.setMinimumValue(0);enh.setMaximumValue(.3*REFLECTANCE_DIVISOR);setter(enh)
    rgb.setRenderer(renderer);project.addMapLayer(rgb)
    pre=QgsRasterLayer(str(run/'CN01_PRELABEL_NOT_FINAL.tif'),'全域候选_未复核')
    pre.setRenderer(QgsPalettedRasterRenderer(pre.dataProvider(),1,[QgsPalettedRasterRenderer.Class(v,QColor(COLORS[v]),NAMES[v]) for v in NAMES]));pre.renderer().setOpacity(.45);project.addMapLayer(pre)
    vector=QgsVectorLayer(gp+'|layername=label_polygons','待复核多边形_编辑此图层','ogr')
    cats=[]
    for c,label in NAMES.items():
        sym=QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':COLORS[c],'outline_width':'0.2'});cats.append(QgsRendererCategory(c,sym,label))
    vector.setRenderer(QgsCategorizedSymbolRenderer('class_id',cats));project.addMapLayer(vector)
    points=QgsVectorLayer(str(run/'facility_review_points.geojson'),'煤炭设施线索_点不是边界','ogr');project.addMapLayer(points)
    reasonlayer=QgsRasterLayer(str(run/'CN01_review_reasons.tif'),'复核原因位掩码_详见说明');project.addMapLayer(reasonlayer);project.layerTreeRoot().findLayer(reasonlayer.id()).setItemVisibilityChecked(False)
    project.viewSettings().setDefaultViewExtent(__import__('qgis.core',fromlist=['QgsReferencedRectangle']).QgsReferencedRectangle(rgb.extent(),project.crs()))
    project_file=str(run/'CN01_review.qgz')
    if not project.write(project_file):raise RuntimeError('QGIS工程保存失败；栅格与矢量仍在输出目录。')
    # Show the completed project in this QGIS session without requiring a manual import.
    if not current.read(project_file):raise RuntimeError('工程已保存，但当前QGIS未能打开，请双击输出qgz。')
    print('完成全域预标注，未完成正式标注。输出目录：',run)
    print('打开多边形属性表，筛选 verified = 0 逐块复核；不得批量把未看过的区域设为已复核。')
    return run

if __name__ in ('__main__','__console__') or 'iface' in globals():
    try:main()
    except Exception:
        traceback.print_exc()
        print('运行未完成：请复制上方完整报错。不要把部分输出当最终结果。')
        raise
