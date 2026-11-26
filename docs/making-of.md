# 大永和像素地圖怎麼做

在大永和地圖裡，街道、建物和圖釘使用同一套地理座標，所以可以從保福宮一路平移到河岸。選「低精度」可以用上一版的模型作對照，切換時鏡頭會停在同一處。[開啟互動地圖](https://clarencechien.github.io/pixelartpoc/)

## 把地圖資料拼成一座城市

Python 建置程式先把經緯度換成以公尺計算的平面座標，依永和區界裁切，並向北保留跨河橋段。OpenStreetMap 提供道路、園界、步道、水域與設施位置。建物取自國土測繪中心三維建物模型的衍生 PMTiles，程式會把跨圖磚的同一棟建物接回來。這版包含 17,305 筆帶高度的輪廓，另以 182 筆 OSM 輪廓補足空缺。[資料來源與授權](../README.md#資料來源與示意範圍) · [建物拼接程式](../tools/city/nlsc.py)

接著把道路、草地和水域畫到底圖。低精度沿著輪廓拉出外牆與屋頂。特色版在相同資料上，依高度、平面形狀與臨路方向組合斜頂、退台、騎樓、遮棚與陽台。資料可以定位一棟建物，個別窗戶的樣式、鐵皮顏色和屋頂設備則由程式配色與造型。[建置程式](../tools/city/build.py) · [建築造型程式](../tools/city/architecture.py)

## 六個地標如何辨認

| 地標 | 建模依據與取捨 |
| --- | --- |
| 中正橋 | 沿車道線配置橋面和鋼拱，讓吊索從兩側拱肋落到橋緣。 |
| 川端橋 | 依 OSM 兩段舊橋中心線定位，沿線鋪設約六公尺寬的步道。橋下畫出雙柱拱形橋墩和鋼板梁，橋上加了復古護欄。橋墩間距為示意。 |
| 頂溪站二號出口 | 用北捷地址和 OSM 出口點對到永和路二段 233 號。保留建物資料裡的大樓輪廓及高度，在朝街的一樓留出內凹入口，配置站名牌、柱和階梯。入口寬深、招牌和材質依街景近似。 |
| 樂華夜市 | 依永平路及市場範圍排列攤車，將入口招牌、條紋棚面、櫃台和燈籠拆成獨立零件。 |
| 永和保福宮 | 用寺廟用地定位，沿縱深堆出前後殿、重簷和上翹的屋脊，另畫廊柱、匾額、燈籠。 |
| 仁愛公園 | 在 OSM 的園界內保留步道和中央草坪。用音樂台與看台的相對位置決定舞台朝向，搭出頂棚與扇形座位。溜冰場依場地輪廓畫跑道，北側遊戲場以城堡平台和滑梯呈現。可從公園筆記點選這三處近看。 |

頂溪站的位置可用北捷出口資訊核對，外觀可和標明二號出入口的街景照片比對。[臺北捷運・頂溪站](https://web.metro.taipei/pages2026/WebStation/045/1) · [雪雨73攝，2025 年二號出入口照片](https://commons.wikimedia.org/wiki/File:捷運頂溪站2號出入口.jpg)

川端橋的橋型參考歷史建築登錄資料與改建工程說明。公園設施參考永和區公所的現場照片，模型中的色彩、座位排數與遊具細節是像素化取捨。[國家文化記憶庫・川端橋](https://tcmb.culture.tw/zh-tw/detail?id=20150901000001&indexCode=BOCH_CountryCulture_12) · [中正橋改建工程](https://wedid.ntpc.gov.tw/governance/detail/53dPrMo7vm2Z) · [永和區公所・仁愛公園](https://www.yonghe.ntpc.gov.tw/home.jsp?id=42e0a4b1406e7972)

## 如何畫到瀏覽器裡

像素堆疊的概念來自 sprite-stacking：把不同高度的水平切片依序疊起來，旋轉時仍能看到體積。全區版改用 WebGL 三角網格，讓前方房屋能遮住後方的牆面；樹冠仍由多層水平環構成。色塊、有限色盤和最近鄰取樣保留像素感。[sprite-stacking 參考專案](https://github.com/danielwh2/sprite-stacking) · [全區繪圖程式](../dist/district-render.js)

建置程式把模型依 256 公尺方格和細節層級輸出成壓縮網格。瀏覽器載入所選精度，繪圖時略過畫面外的方格，拉近才畫細部。無法使用 WebGL 時，改以預先繪好的平面圖顯示街廓；圖釘和走讀線可以照常操作。[平面圖產生程式](../tools/city/roofmap.py)

## 走讀線如何產生

程式將中正橋、頂溪站和樂華夜市對到最近的道路節點，以道路長度為主要成本，用 Dijkstra 演算法求出兩段相接的路徑。建置後把折線座標存入 `dist/city/district.json`。按「顯示走讀線」時，程式依目前螢幕大小安排俯視鏡頭，把兩段線與三站一起放進畫面。這條約 1.37 公里的線供地圖導覽，現場的人行動線與通行狀況仍要看道路標示。[開啟走讀線](https://clarencechien.github.io/pixelartpoc/?place=route) · [鏡頭與路線程式](../dist/district.js)

## 雙橋剖面怎麼切

在主地圖按「雙橋剖面」會將鏡頭移到兩座橋。A 在西側、B 在東側。可旋轉、平移或縮放地圖，紅線會跟著橋的位置投影；關閉剖面可回到原視角。拖動紅線或滑桿時，東西向的垂直剖切面會在主跨內從永和側逐步移向臺北側。可用三個定位鍵比較舊橋墩、兩墩之間與新橋吊索。在滑桿上按方向鍵，每次移動 0.25 公尺。[開啟雙橋剖面](https://clarencechien.github.io/pixelartpoc/?place=kawabata&section=bridges)

建置時沿用特色版的橋面、拱肋、吊索和橋墩造型，另存各個凸形構件的頂點。瀏覽器找出構件各邊與當前平面的交點，依水平方向和高度畫出截面。兩橋共用相同的水平與垂直比例。滑桿距離從本次剖切範圍的南端起算；縱軸是模型相對高度，橋墩間距為美術示意。地圖在目前模型的零點截斷，沒有河床測量資料。[剖面資料產生程式](../tools/city/sections.py) · [剖切與互動程式](../dist/bridge-section.js)

## 本機查看與重建

只想查看成品，可以在儲存庫根目錄執行 `python3 -m http.server 8000 --directory dist`，瀏覽器開啟 `http://localhost:8000/`。要修改地標造型，編輯 `tools/city/architecture.py`，再用下列指令重建。第一個參數是放置 OSM Parquet 分檔的資料夾，第二個是新北市建物圖檔。招牌繪製需安裝 Noto Sans CJK TC 粗體。[原始資料下載位置](../README.md#資料來源與示意範圍)

```sh
python3 -m pip install duckdb 'shapely>=2.1' numpy pillow pmtiles mapbox-vector-tile
python3 tools/city/build.py /path/to/elements /path/to/nlsc-new-taipei.pmtiles
python3 tools/icons.py
```

地標選單、近看視角和走讀線操作在 `dist/district.js`。修改操作只需重新載入網頁。發布時，將 `main` 的 `dist/` 內容放到 `gh-pages` 分支根目錄，GitHub Pages 即會提供同一份靜態地圖。
