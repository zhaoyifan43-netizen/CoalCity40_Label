# CoalCity-40 PyQGIS Windows starter

## 这一步会做什么
- 扫描 `D:\CoalCity\input` 中的栅格与矢量数据；
- 把可读取的数据图层加载进 QGIS；
- 输出数据清单 CSV（路径、类型、坐标系、范围、栅格尺寸、波段数）；
- 创建可编辑的 GeoPackage 多边形层 `label_polygons`，字段为：
  - `class_id`：类别 0–13；255 仅用于显式 Ignore；尚未判定时允许为空
  - `verified`：0=未复核，1=已人工确认
  - `evidence`：用于记录辅助证据
  - `note`：备注
- 保存 QGIS 工程。

## 路径
- 输入：`D:\CoalCity\input`
- 输出：`D:\CoalCity\output`
- 工具目录：`D:\CoalCity\qgis_tools`

## 运行步骤
1. 在 Windows 资源管理器中创建 `D:\CoalCity\qgis_tools`。
2. 将 `00_prepare_workspace.py` 放入该目录。
3. 打开 QGIS。
4. 菜单 **插件 → Python 控制台**（不同版本菜单名称可能略有不同）。
5. 在控制台输入并回车：

```python
exec(open(r"D:\CoalCity\qgis_tools\00_prepare_workspace.py", encoding="utf-8").read())
```

6. 检查 QGIS 是否加载了数据图层；检查 `D:\CoalCity\output` 中是否生成：
   - `CN01_Datong_input_inventory.csv`
   - `CoalCity40_CN01_Datong_review.gpkg`
   - `CoalCity40_CN01_Datong_review.qgz`

## 重要限制
本脚本是初始化和数据盘点，不会根据文件名猜类别，也不会自动把未确认区域设为 Ignore。
自动预标注必须在检查真实数据后再配置：Sentinel-2 波段顺序、NDVI/NDBI/NDWI、地表温度、夜光、不透水面比例、CUFR 边界和影像网格是否对齐，都会影响结果。
请先运行脚本，把生成的 `CN01_Datong_input_inventory.csv` 上传给 ChatGPT。后续再生成与真实文件结构匹配的预标注脚本。
