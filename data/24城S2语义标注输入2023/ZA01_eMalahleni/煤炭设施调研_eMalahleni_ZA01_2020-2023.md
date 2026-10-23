---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'd6debaca-5f80-4c34-8403-a21b3f1f8aff'
  PropagateID: 'd6debaca-5f80-4c34-8403-a21b3f1f8aff'
  ReservedCode1: 'b70cd5bf-b33d-4d06-86ed-d6f04ca31fb8'
  ReservedCode2: 'b70cd5bf-b33d-4d06-86ed-d6f04ca31fb8'
---

# 煤炭设施调研：ZA01 eMalahleni（南非·普马兰加省）2020–2023

> CoalCity-40 数据集 S2 语义标注辅助证据 · 基准年份 2023
> **CUFR 中心**：25.89165°S, 29.22906°E，半径 20 km
> **数据来源**：Global Energy Monitor（GEM Wiki / Global Coal Mine Tracker，经 Wayback 存档）、Wikipedia（英文）、Seriti 官网（经 Wayback 存档）、Thungela 官网（经 Wayback 存档）、学术文献（ResearchGate）、OpenStreetMap（设施地块）
> **坐标体系**：WGS 84。坐标分级：**GEM 精确**（GEM 设施级精确坐标）/ **维基坐标**（Wikipedia infobox）/ **OSM 地块**（OpenStreetMap mine/industrial 设施面中心）
> **数据访问说明**：GEM Wiki 直连被网络环境阻断，本文数据经 **Wayback Machine 存档**访问 gem.wiki 页面获取；Seriti/Thungela 官网直连部分受限，同样经 Wayback 存档访问
> （拆分自《煤炭设施调研_南非eMalahleni_Middelburg_ZA01_ZA02_2020-2023.md》，2026-10；本版为证据级修订版，2026-10-13）

## 一、Witbank 煤田与城市背景

- **Witbank Coalfield（维特班克煤田）**是南非最重要的煤田之一，位于普马兰加省 Highveld 高原，与 Highveld 煤田相连，构成南非动力煤主产区。煤田内大量煤矿以**坑口方式直供 Eskom 燃煤电厂**，同时经 **Richards Bay Coal Terminal（RBCT）** 出口（Thungela/Seriti 官网、GEM）
- 煤种以**低灰分烟煤（bituminous thermal coal）**为主，热值高，是南非出口煤的主力
- 该地区煤矸石堆（discard dumps）存在**自燃现象**，有学术文献专门研究，是语义标注中矸石堆（类别 8-12 中"矸石/渣堆"类）的重要参考
- **eMalahleni（Witbank）**：南非普马兰加省城市，原名 Witbank（阿非利卡语"白脊"），2006 年更名为 eMalahleni（祖鲁语"煤之地"）。1903 年建城，是南非最重要的煤业中心城市之一，围绕其建有多座 Eskom 电厂与大型露天/井工煤矿（Wikipedia "Witbank"）

## 二、主要煤炭设施（CUFR 20km 内，3 个）

### 1. Khwezela 煤矿（含原 Landau + Kleinkopje 合并）

- **类型**：露天+井工（opencast/underground）；坐标 **-25.926243, 29.155635（exact，GEM）**，距中心约 **8.3 km**
- **产能**：GEM 记录（2023 年前后）；**业主**：Thungela（2021 年 6 月从 Anglo American 分拆）
- **说明**：Khwezela = 原 **Landau 煤矿 + Kleinkopje 煤矿**合并后的运营单元；Landau Colliery 也是同名聚居地（2011 人口 1,029 人，Emalahleni 地方自治市辖区，Wikipedia "Landau Colliery"）
- **状态**：2023 年前后**运营中**（Thungela 7 大矿区之一，经 Wayback 2023/2024 官网确认）
- **来源**：https://www.gem.wiki/Khwezela_Coal_Mine；https://en.wikipedia.org/wiki/Landau_Colliery；Thungela 官网（Wayback 存档）

### 2. Greenside 煤矿（Greenside Colliery）

- **类型**：露天+井工（opencast/underground）；坐标 **-25.960979, 29.18545（exact，GEM）**，距中心约 **8.9 km**
- **业主**：Thungela（2021 年分拆自 Anglo）；**状态**：2023 年**运营中**（Thungela 7 大矿区之一）
- **说明**：Greenside 也是同名聚居地（2011 年普查 428 户），曾有大量煤矿（Wikipedia "Greenside Colliery"）
- **来源**：https://www.gem.wiki/Greenside_coal_mine；https://en.wikipedia.org/wiki/Greenside_Colliery

### 3. Duvha 电厂（Duvha Power Station）

- **类型**：燃煤电厂（Eskom）；坐标 **-25.96388889, 29.33722222（Wikipedia infobox）**，距中心约 **13.5 km**
- **规模**：装机 3,600 MW（6×600 MW）；**2023 年前后运营中**
- **煤源**：由 **MMS（Middelburg Mine Services）** 等煤矿坑口直供（Seriti 官网）
- **来源**：https://en.wikipedia.org/wiki/Duvha_Power_Station

## 三、周边补充（20–50km，13 个）

### 1. MMS（Middelburg Mine Services，原 Wolvekrans-Middelburg Complex）

- **坐标 -25.899444, 29.460556（exact，GEM）**，距 eMalahleni 中心约 **23.2 km**
- **产能**：Seriti 官网称 **7 Mtpa** 供 Duvha 电厂（另有资料 8 Mtpa 设计/6.1 Mt 2023 产）
- **业主**：**Seriti**（2021 年 6 月从 South32 收购 SAEC 获得）；**状态**：2023 年**运营中**
- **来源**：https://www.gem.wiki/Middelburg_Mining_Services；Seriti 官网（Wayback 存档）

### 2. Klipspruit 煤矿（Seriti）

- **坐标**：**-26.037399, 29.033290（OSM 地块，mine）**，距 eMalahleni 中心约 **25.4 km**（原报告"Ogies 附近 5km"估算坐标已替换为 OSM 实测地块中心，位于 Ogies 镇西南）
- **产能**：2.4 Mtpa 供 Eskom + 0.35 Mtpa 国内 + 约 5.1 Mtpa 出口（RBCT）；2003 年建矿，服务年限至 2048
- **业主**：**Seriti**（2021 年 6 月从 South32 收购）；**状态**：2023 年**运营中**
- **来源**：Seriti 官网 Klipspruit 页（Wayback 存档）；OSM 地块

### 3. Phola 洗煤厂（Phola Coal Processing Plant）

- **坐标**：**-26.052500, 29.025508（OSM 地块，industrial）**，距 eMalahleni 约 **27.1 km**（与 Klipspruit 同区，Ogies/Phola 镇附近；原估算坐标已替换为 OSM 实测）
- **规模**：设计产能 16 Mtpa；**运营**：Thungela（原 Anglo）与 BHP 各持 50%（2023 年前后）
- **状态**：2023 年**运营中**；洗选 Klipspruit/Phola 周边出口煤
- **说明**：Phola 是 eMalahleni 本地自治市内的居民点（2011 普查人口 31,885），洗煤厂以地名为名（Wikipedia "Phola, Mpumalanga"）
- **来源**：https://www.gem.wiki/Phola_coal_preparation_plant（如有）；Thungela/BHP 公开资料；OSM 地块

### 4. Goedehoop 煤矿（Thungela）

- **坐标**：**-26.1033988, 29.407282（exact，GEM）**，距 eMalahleni 约 **29.5 km**
- **业主**：Thungela；**产能**：出口为主（RBCT）；2023 年运营中
- **说明**：Thungela 计划 2025 年前后关闭（GEM）
- **来源**：https://www.gem.wiki/Goedehoop_coal_mine

### 5. Komati 电厂（Eskom）

- **坐标**：-26.09, 29.47194444（Wikipedia），距 eMalahleni 约 **32.8 km**
- **规模**：1,000 MW（9 台）；**状态**：2022 年 10 月起因无长期煤供应协议进入维护性停机（GEM/Wikipedia）
- **来源**：https://en.wikipedia.org/wiki/Komati_Power_Station

### 6. Kendal 电厂（Eskom）

- **坐标**：-26.090285, 28.968796（exact，GEM），距 eMalahleni 约 **34.1 km**
- **规模**：4,116 MW（6×686 MW），南非最大燃煤电厂之一；2039–2044 退役计划
- **煤源**：Khutala 与 Klipspruit 供应（Seriti 官网）
- **来源**：https://www.gem.wiki/Kendal_power_station；https://en.wikipedia.org/wiki/Kendal_Power_Station

### 7. Khutala 煤矿（Seriti）

- **坐标**：-26.124001, 29.003424（exact，GEM），距 eMalahleni 约 **34.3 km**
- **产能**：5.5–7 Mtpa（口径不同）；1986 年建矿，**2021 年 6 月从 South32 收购**；供 Kendal 电厂至 2033
- **状态**：2023 年**运营中**（井工+露天，bord-and-pillar）
- **来源**：https://www.gem.wiki/Khutala_Coal_Mine；Seriti 官网 Khutala 页（Wayback）

### 8. Kriel 煤矿（Seriti）

- **坐标**：-26.225785, 29.136045（exact，GEM），距 eMalahleni 约 **38.3 km**
- **产能**：约 4 Mtpa 供 Kriel 电厂；1975 年建；**2018 年从 Anglo American 收购**；资源至 2035
- **状态**：2023 年**运营中**（井工 bord-and-pillar + 露天 dragline）
- **来源**：https://www.gem.wiki/Kriel_Coal_Mine；Seriti 官网 Kriel 页（Wayback）

### 9. Optimum 煤矿（Optimum Coal Mine）

- **坐标**：-26.0048466, 29.6114906（exact，GEM），距 eMalahleni 约 **40.3 km**
- **状态**：2022 年**进入 Care & Maintenance**（此前因供 Hendrina 电厂关闭而停产；2020-2022 业务救助）
- **来源**：https://www.gem.wiki/Optimum_coal_mine

### 10. Kriel 电厂（Eskom）

- **坐标**：-26.2542, 29.17944（Wikipedia），距 eMalahleni 约 **40.6 km**
- **规模**：3,000 MW（6×500）；**状态**：2023 年前后运营中（Eskom 主要电厂之一）
- **煤源**：Kriel 煤矿坑口直供
- **来源**：https://en.wikipedia.org/wiki/Kriel_Power_Station

### 11. Zibulo 煤矿（Thungela 73% / Inyosi Coal 27%）

- **坐标**：-26.1994277, 29.0084596（exact，GEM），距 eMalahleni 约 **40.7 km**
- **状态**：2023 年运营中（出口+国内）；Thungela 7 矿区之一
- **来源**：https://www.gem.wiki/Zibulo_coal_mine

### 12. Matla 煤矿（Exxaro）

- **坐标**：-26.26345, 29.12681（exact，GEM），距 eMalahleni 约 **42.6 km**
- **产能**：约 10 Mtpa；**业主**：Exxaro Resources；供 Matla 电厂
- **状态**：2023 年运营中
- **来源**：https://www.gem.wiki/Matla_Coal_Mine

### 13. Matla 电厂（Eskom）

- **坐标**：-26.2825, 29.14083333（Wikipedia），距 eMalahleni 约 **44.3 km**
- **规模**：3,600 MW（6×600）；**煤源**：Matla 煤矿坑口
- **来源**：https://en.wikipedia.org/wiki/Matla_Power_Station

## 四、背景参考（50km 以外，供上下文）

| 设施 | 坐标 | 距 ZA01 | 说明 |
|---|---|---|---|
| Mafube 煤矿（Exxaro/Anglo 各 50%） | -25.794651, 29.737834 | 约 52 km | 出口矿约 4.5 Mtpa（RBCT），2023 年运营中 |
| Arnot 煤矿（封存） | -25.934846, 29.774760 | 约 55 km | 2015 年关闭，mothballed |
| Arnot 电厂（Eskom） | -25.94384, 29.78956 | 约 56 km | 2,100 MW（6×350）；2020-2024 机组逐步退役 |
| Isibonelo 煤矿（Thungela） | -26.435276, 29.208912 | 约 60 km | 7 矿区之一，供 Sasol Secunda |
| New Denmark 煤矿（Seriti） | -26.740050, 29.309011 | 约 95 km | 2018 从 Anglo 收购，供 Tutuka 电厂 |
| New Vaal 煤矿（Seriti） | 约 -27.0, 26.9（Free State，估） | >200 km | 16 Mtpa 供 Lethabo 电厂，属 Highveld 煤田 |

## 五、数据说明与限制

1. **来源分级**：核心设施坐标/产能取自 **GEM Global Coal Mine Tracker**（2024–2026 版次，经 Wayback 访问）；状态/运营方以 **Seriti、Thungela 官网（Wayback 2023/2024 存档）** 为准；背景来自 Wikipedia
2. **口径差异**：GEM 的"产能"为设计产能（Mtpa），公司官网的 Mtpa 为实际/合同量，两者可能有差异（如 Khutala：GEM 记录 vs Seriti 官网 5.5–7 Mtpa）
3. **坐标精度**：GEM"exact"坐标可直接地图定位；原报告 Klipspruit/Phola 估算坐标已替换为 **OSM 地块实测**（25.4/27.1 km），可作制图级坐标；Kleinkopje 井场另获 OSM 旁证（-26.012322, 29.230542，13.4 km，属 Khwezela 运营单元的一部分，可作 Khwezela 多井场布局参考）
4. **时间口径**：2023 年前后状态以 2022–2024 公开资料为准，重点标注了 Seriti 2021-06 收购 SAEC（South32）与 2018 收购 Anglo Eskom 相关资产、Thungela 2021 从 Anglo 分拆等关键事实变更
5. **未覆盖项**：eMalahleni 市区内历史遗留矸石堆（自燃点）的具体坐标未找到权威标注（仅有 Witbank 煤田矸石自燃的学术文献）；Middelburg 本地其他小设施（如 Middelburg CHP）未获可靠资料
6. 本报告为调研性成果，未做实地核查；距离均按 WGS84 大圆距离计算；数据请以各来源原页为准
7. **本次证据级修订**：Klipspruit/Phola 原估算坐标替换为 OSM 地块实测坐标（可作制图级使用）；补 Kleinkopje OSM 旁证；无剩余"待核实"项

## 六、关键参考文献

- Witbank coalfield 矸石自燃：*Spontaneous combustion of the organic matter in discards from the Witbank coalfield*（ResearchGate）https://www.researchgate.net/publication/292646987
- Seriti 2018 收购 Anglo Eskom 关联资产（New Vaal/New Denmark/Kriel + 4 座关闭矿）：https://seritiza.com/news-media/media-coverage/2018/anglo-american-plc-anglo-american-completes-sale-of-eskom-tied-thermal-coal-operations-in-south-africa/（Wayback 存档）
- Seriti 2021-06 收购 South32/SAEC（含 Khutala/Klipspruit/MMS）及 6 矿产能表：https://seritiza.com/（Wayback 存档）
- Thungela 7 矿区（Zibulo/Goedehoop/Greenside/Isibonelo/Khwezela/Mafube 等）：https://www.thungela.com/about-us/where-we-operate/（Wayback 2023/2024 存档）
- Witbank 煤田：https://en.wikipedia.org/wiki/Witbank_Coalfield
- eMalahleni：https://en.wikipedia.org/wiki/Witbank

（证据级修订：2026-10-13；数据截至 2024 年公开资料；GEM/Seriti/Thungela 页面经 Wayback Machine 存档访问）