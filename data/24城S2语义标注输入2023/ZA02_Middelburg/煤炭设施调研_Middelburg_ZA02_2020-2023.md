---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'caec7d83-dbbf-49b1-a486-040727a3ddf2'
  PropagateID: 'caec7d83-dbbf-49b1-a486-040727a3ddf2'
  ReservedCode1: '9ad72c45-a741-4fe1-a724-b09bf8c7ef01'
  ReservedCode2: '9ad72c45-a741-4fe1-a724-b09bf8c7ef01'
---

# 煤炭设施调研：ZA02 Middelburg 米德尔堡（南非·普马兰加省）2020–2023

> CoalCity-40 数据集 S2 语义标注辅助证据 · 基准年份 2023
> **CUFR 中心**：25.76802°S, 29.45095°E，半径 20 km
> **数据来源**：Global Energy Monitor（GEM Wiki / Global Coal Mine Tracker，经 Wayback 存档）、Wikipedia（英文）、Seriti 官网（经 Wayback 存档）、Thungela 官网（经 Wayback 存档）、学术文献（ResearchGate）
> **坐标体系**：WGS 84。坐标分级：**GEM 精确**（GEM 设施级 exact 坐标）/ **维基坐标**（Wikipedia infobox）
> **数据访问说明**：GEM Wiki 直连被网络环境阻断，本文数据经 **Wayback Machine 存档**访问 gem.wiki 页面获取；Seriti/Thungela 官网直连部分受限，同样经 Wayback 存档访问
> （拆分自《煤炭设施调研_南非eMalahleni_Middelburg_ZA01_ZA02_2020-2023.md》，2026-10；本版为证据级修订版，2026-10-13）

## 一、Witbank 煤田与城市背景

- **Witbank Coalfield（维特班克煤田）**是南非最重要的煤田之一，位于普马兰加省 Highveld 高原，与 Highveld 煤田相连，构成南非动力煤主产区。煤田内大量煤矿以**坑口方式直供 Eskom 燃煤电厂**，同时经 **Richards Bay Coal Terminal（RBCT）** 出口（Thungela/Seriti 官网、GEM）
- 煤种以**低灰分烟煤（bituminous thermal coal）**为主，热值高，是南非出口煤的主力
- 该地区煤矸石堆（discard dumps）存在**自燃现象**，有学术文献专门研究，是语义标注中矸石堆（类别 8-12 中"矸石/渣堆"类）的重要参考
- **Middelburg（米德尔堡）**：普马兰加省大型镇，位于 eMalahleni 以东约 30 km。周边有 MMS（Middelburg Mine Services）等煤矿及 Mafube 等出口矿（Wikipedia "Middelburg, Mpumalanga"）

## 二、主要煤炭设施（CUFR 20km 内，1 个）

### 1. MMS（Middelburg Mine Services）

- **坐标**：-25.899444, 29.460556（exact，GEM），距 Middelburg CUFR 中心约 **14.6 km**
- **产能**：约 7 Mtpa 露天，直供 Duvha 电厂（Eskom）；另有资料 8 Mtpa 设计/6.1 Mt 2023 产
- **业主**：**Seriti**（2021-06 从 South32/SAEC 收购）；**状态**：2023 年**运营中**
- **说明**：原 Wolvekrans-Middelburg Complex，Seriti 2021 年收购 SAEC 时一并获得
- **来源**：https://www.gem.wiki/Middelburg_Mining_Services；Seriti 官网（Wayback）

## 三、周边补充（20–50km，9 个）

### 1. Duvha 电厂（Eskom）

- **坐标**：-25.963889, 29.337222（Wikipedia infobox），距 Middelburg 约 **24.6 km**
- **规模**：3,600 MW（6×600 MW）；**2023 年前后运营中**
- **煤源**：由 MMS 等煤矿坑口直供（Seriti 官网）
- **来源**：https://en.wikipedia.org/wiki/Duvha_Power_Station

### 2. Mafube 煤矿（Exxaro / Anglo 各 50%）

- **坐标**：-25.794651, 29.737834（exact，GEM），距 Middelburg 约 **28.9 km**
- **产能**：约 4.5 Mtpa 出口（RBCT）；**状态**：2023 年运营中
- **来源**：https://www.gem.wiki/Mafube_coal_mine

### 3. Optimum 煤矿（Optimum Coal Mine）

- **坐标**：-26.004847, 29.611471（exact，GEM），距 Middelburg 约 **30.8 km**
- **状态**：2022 年**进入 Care & Maintenance**（此前因供 Hendrina 电厂关闭而停产；2020-2022 业务救助）
- **来源**：https://www.gem.wiki/Optimum_coal_mine

### 4. Greenside 煤矿（Thungela）

- **坐标**：-25.960979, 29.18545（exact，GEM），距 Middelburg 约 **34.1 km**
- **类型**：露天+井工；业主 Thungela（2021 年分拆自 Anglo）；**2023 年运营中**（Thungela 7 大矿区之一）
- **来源**：https://www.gem.wiki/Greenside_coal_mine

### 5. Khwezela 煤矿（Thungela）

- **坐标**：-25.926243, 29.155635（exact，GEM），距 Middelburg 约 **34.4 km**
- **类型**：露天+井工；原 **Landau 煤矿 + Kleinkopje 煤矿**合并后的运营单元；业主 Thungela；**2023 年运营中**
- **来源**：https://www.gem.wiki/Khwezela_Coal_Mine

### 6. Komati 电厂（Eskom）

- **坐标**：-26.09, 29.47194444（Wikipedia），距 Middelburg 约 **35.9 km**
- **规模**：1,000 MW（9 台）；**状态**：2022 年 10 月起因无长期煤供应协议进入维护性停机（GEM/Wikipedia）
- **来源**：https://en.wikipedia.org/wiki/Komati_Power_Station

### 7. Arnot 煤矿（已闭矿/封存）

- **坐标**：-25.9348458, 29.7747599（exact，GEM），距 Middelburg 约 **37.3 km**
- **状态**：2015 年关闭，mothballed；曾被收购尝试重启（2020-2022 期间谈判）
- **来源**：https://www.gem.wiki/Arnot_coal_mine

### 8. Goedehoop 煤矿（Thungela）

- **坐标**：-26.1033988, 29.407282（exact，GEM），距 Middelburg 约 **37.5 km**
- **产能**：出口为主（RBCT）；2023 年运营中；Thungela 计划 2025 年前后关闭（GEM）
- **来源**：https://www.gem.wiki/Goedehoop_coal_mine

### 9. Arnot 电厂（Eskom）

- **坐标**：-25.94384, 29.78956（Wikipedia），距 Middelburg 约 **39.1 km**
- **规模**：2,100 MW（6×350）；**状态**：2020-2024 期间机组逐步退役/关闭（部分机组由私人购电重启计划未落实）
- **来源**：https://en.wikipedia.org/wiki/Arnot_Power_Station

## 四、背景参考（50km 以外，供上下文）

| 设施 | 坐标 | 距 ZA02 | 说明 |
|---|---|---|---|
| Isibonelo 煤矿（Thungela） | -26.435276, 29.208912 | 约 78 km（拆分时推算） | 7 矿区之一，供 Sasol Secunda；距 ZA01 约 60 km |
| New Denmark 煤矿（Seriti） | -26.740050, 29.309011 | 约 109 km（拆分时推算） | 2018 从 Anglo 收购，供 Tutuka 电厂；距 ZA01 约 95 km |
| New Vaal 煤矿（Seriti） | 约 -27.0, 26.9（Free State，估） | >200 km | 16 Mtpa 供 Lethabo 电厂，属 Highveld 煤田 |

> 注：Isibonelo/New Denmark 距 ZA02 的距离为本拆分时按 GEM 坐标与 CUFR 中心推算（大圆距离），原报告仅给出距 ZA01 的距离。

## 五、数据说明与限制

1. **来源分级**：核心设施坐标/产能取自 **GEM Global Coal Mine Tracker**（2024–2026 版次，经 Wayback 访问）；状态/运营方以 **Seriti、Thungela 官网（Wayback 2023/2024 存档）** 为准；背景来自 Wikipedia
2. **口径差异**：GEM 的"产能"为设计产能（Mtpa），公司官网的 Mtpa 为实际/合同量，两者可能有差异
3. **坐标精度**：GEM"exact"坐标可直接地图定位；本报告无估算坐标项、无"待核实"项；MMS 坐标与 ZA01 报告同源
4. **时间口径**：2023 年前后状态以 2022–2024 公开资料为准，重点标注了 Seriti 2021-06 收购 SAEC（South32）、Thungela 2021 从 Anglo 分拆等关键事实变更；Komati 2022-10 维护性停机、Optimum 2022 Care & Maintenance、Arnot 矿 2015 封存均已按事件年份标注
5. **未覆盖项**：Middelburg 本地其他小设施（如 Middelburg CHP）未获可靠资料
6. 本报告为调研性成果，未做实地核查；距离均按 WGS84 大圆距离计算；数据请以各来源原页为准

## 六、关键参考文献

- Witbank coalfield 矸石自燃：*Spontaneous combustion of the organic matter in discards from the Witbank coalfield*（ResearchGate）https://www.researchgate.net/publication/292646987
- Seriti 2018 收购 Anglo Eskom 关联资产：https://seritiza.com/news-media/media-coverage/2018/anglo-american-plc-anglo-american-completes-sale-of-eskom-tied-thermal-coal-operations-in-south-africa/（Wayback 存档）
- Seriti 2021-06 收购 South32/SAEC（含 Khutala/Klipspruit/MMS）：https://seritiza.com/（Wayback 存档）
- Thungela 7 矿区：https://www.thungela.com/about-us/where-we-operate/（Wayback 2023/2024 存档）
- Middelburg, Mpumalanga：https://en.wikipedia.org/wiki/Middelburg,_Mpumalanga

（证据级修订：2026-10-13；数据截至 2024 年公开资料；GEM/Seriti/Thungela 页面经 Wayback Machine 存档访问）