# -*- coding: utf-8 -*-
"""Diagnostic masks only; does not alter source imagery or final labels."""
import os, traceback
import numpy as np
from osgeo import gdal
from qgis.core import QgsProject, QgsRasterLayer
INPUT_DIR=r"D:\CoalCity\input\CN01_Datong"
OUT=r"D:\CoalCity\output\scl_diagnostic"
def log(s): print("[CoalCity-SCL-Diagnostic] "+str(s))
def read(p):
 d=gdal.Open(p,gdal.GA_ReadOnly)
 if d is None: raise RuntimeError("Cannot read: "+p)
 return d,d.GetRasterBand(1).ReadAsArray(),d.GetRasterBand(1).GetNoDataValue()
def write(ref,p,a):
 drv=gdal.GetDriverByName("GTiff")
 if os.path.exists(p): drv.Delete(p)
 d=drv.Create(p,ref.RasterXSize,ref.RasterYSize,1,gdal.GDT_Byte,options=["COMPRESS=LZW","TILED=YES"])
 d.SetGeoTransform(ref.GetGeoTransform()); d.SetProjection(ref.GetProjection())
 b=d.GetRasterBand(1); b.WriteArray(a.astype(np.uint8)); b.SetNoDataValue(0); b.FlushCache(); d=None
def main():
 os.makedirs(OUT,exist_ok=True)
 sd,s, sn=read(os.path.join(INPUT_DIR,"CN01_SCL.tif"))
 wd,w,wn=read(os.path.join(INPUT_DIR,"CN01_NDWI.tif"))
 vd,v,vn=read(os.path.join(INPUT_DIR,"CN01_NDVI.tif"))
 if not (s.shape==w.shape==v.shape): raise RuntimeError("SCL/NDWI/NDVI sizes differ.")
 if sd.GetGeoTransform()!=wd.GetGeoTransform() or sd.GetProjection()!=wd.GetProjection(): raise RuntimeError("SCL and NDWI grids/CRS differ.")
 if sd.GetGeoTransform()!=vd.GetGeoTransform() or sd.GetProjection()!=vd.GetProjection(): raise RuntimeError("SCL and NDVI grids/CRS differ.")
 # Conventional Sentinel-2 SCL: 3 cloud shadow; 6 water; 8/9 cloud; 10 cirrus.
 masks=[
 ("SCL_class6_water.tif",s==6),
 ("SCL_cloud_shadow_class3.tif",s==3),
 ("SCL_cloud_cirrus_classes8_9_10.tif",np.isin(s,[8,9,10])),
 ("SCL_nodata_defect_classes0_1.tif",np.isin(s,[0,1])),
 ("SCL_ignore_classes.tif",np.isin(s,[0,1,3,8,9,10,11])),
 ("NDWI_only_suspect.tif",np.isfinite(w)&np.isfinite(v)&((w!=wn) if wn is not None else True)&((v!=vn) if vn is not None else True)&(w>=0.12)&(v<0.20)&(s!=6)&(~np.isin(s,[0,1,3,8,9,10,11])))]
 project=QgsProject.instance()
 log("SCL value counts:")
 for cls in range(12): log(f"SCL value {cls}: {int(np.count_nonzero(s==cls))}")
 for fn,mask in masks:
  p=os.path.join(OUT,fn); write(sd,p,np.where(mask,1,0))
  lyr=QgsRasterLayer(p,os.path.splitext(fn)[0])
  if lyr.isValid(): project.addMapLayer(lyr)
  log(f"{fn}: {int(np.count_nonzero(mask))} pixels")
 log("只显示 RGB + 一个诊断层进行对比；不会生成正式标签。")
try: main()
except Exception: log(traceback.format_exc())
