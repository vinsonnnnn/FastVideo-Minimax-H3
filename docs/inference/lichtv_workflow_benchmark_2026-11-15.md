# LichTV 全工作流实测报告（2026-11-15）

**测试完成：53/53 项已记录，共59次尝试。** 后台注册50项，另补充首页实际使用的U00、U06两个独立H3模板及M02图像增强模板。

最终结果：成功51项，执行失败2项。已完成请求累计耗时 134.53 分钟，对应请求墙钟等效GPU费用 6.7265 元；此数不是平台完整账单。

已记录测试窗口：650.96分钟，按3元/小时折合32.5479元，包含准备与间隙，但不包括批测前后继续开机的时间。

## 环境与计费口径

- 时间：本报告日期采用北京时间（UTC+8），逐任务原始时间戳保留UTC。
- 调用链：LichTV云端网站经SSH通道连接AutoDL面板/ComfyUI，模型在5090执行；本轮测量没有经过FastVideo服务。
- 单卡 NVIDIA GeForce RTX 5090，32607 MiB；容器内存90 GiB。
- ComfyUI 0.44.0；PyTorch 2.12.1+cu130；Python 3.12.3。实际环境快照见JSON。
- 用户给定租价：3元/小时，单次等效费用 = 请求墙钟秒数 × 3 / 3600。
- API清单及H3补充模板经面板API提交；M02按原生页方式直接提交ComfyUI /prompt。素材已预先放入input目录，计时不含浏览器操作和素材上传。
- 请求墙钟从提交前开始，到收到终态历史为止，包含本次模型加载、编译、推理、解码、保存及约2秒轮询间隔；另列ComfyUI执行起止消息得到的执行秒数。
- 每项测试前请求卸载模型、清理显存；进程和操作系统文件缓存保留。部分通用节点可能命中缓存，不视为严格冷启动或多次运行平均。
- 显存是每秒nvidia-smi采样的最大整卡已用值，不是框架精确峰值；失败提交过快时可能没有采样。
- 本报告按开机时间乘用户给定单价估算，包含准备、空闲等间隙，实际以AutoDL账单为准。云服务器、存储、人工及重抽费用未计入。

## 输入和测试范围

- 视频目标约5秒，基础分辨率约0.4MP（常见864×480）；模型对齐、时长取整和原有后处理会改变实际产出。API清单本轮开放的megapixels字段统一为0.4，包括二采目标尺寸；首页U06首轮保留原生1.0MP设置，另补充0.4MP对照档。固定倍率放大器和后处理步骤仍保留。因此不代表各工作流原始高分辨率默认预设的成本，表中以ffprobe实际输出为准。
- 使用镜像中已有素材的独立副本：人物参考图、5秒动作视频、5秒参考音频；未修改原素材。未提供的可选参考槽位由面板接口处理为空白占位。
- 图像、提示词、语音、动作迁移、后期和连通工作流按各自用途测试，不能统一解释为“生成5秒H3视频”。
- 保留原采样步数、LoRA和后处理；为避免复用采样结果，各工作流设置独立种子。输入覆盖及模板配置逐项列出。
- 单项超时30分钟，仅中止该测试任务；遇到其他用户已排队任务先等待，不清空其他任务。
- 覆盖后台注册的50个本机ComfyUI工作流和首页三个独立模板（U00、U06、M02）。画布中的外部供应商API选项未调用，不能按本机GPU租价推算其收费。
- 这是按用途准备有效输入后的单次功能/成本测试，不是相同输出画质的严格横向基准；多采、超分等会改变产出尺寸。
- 每种测试配置仅作单次记录；输入修正、独立进程复测和分辨率对照分别保留，不能构成稳定性、画质或商业可用率评测。成功仅表示任务成功且产出可读取，媒体文件另做完整解码核验，仍需人工审核画面和声音。
- “折合60秒”按本次成本 × 60 / 实际产出秒数线性换算，仅适用于本表成功的视频生成类记录；不是实际连续生成60秒的测试，也未包含重抽、拼接和空闲。

## 全部结果

| 工作流 | 类别 | 结果 | 实际产出 | 请求秒 | 执行秒 | 本次等效费用/元 | 折合60秒/元 | 显存采样峰值/MiB |
|---|---|---|---|---:|---:|---:|---:|---:|
| API-Z-连通测试 | 连通测试 | 成功 | 864×480 / 0.125s / 无音轨 | 4.947 | 0.203 | 0.0041 | — | 1022.0 |
| API-U06-9图版API-V5 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 93.303 | 86.673 | 0.0778 | 0.903 | 31858.0 |
| API-U00-闹闹版_s | H3视频 | 成功 | 1280×704 / 5.167s / 带音频 | 173.541 | 169.536 | 0.1446 | 1.679 | 31846.0 |
| API-U01-minimax_h3_基础版API | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 170.879 | 167.101 | 0.1424 | 1.654 | 31844.0 |
| API-U02-minimax_h3_图生视频基础版-V2 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 160.807 | 156.781 | 0.1340 | 1.556 | 31838.0 |
| API-U03-minimax_h3_light2v-文生视频加速版API-V2 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 96.778 | 92.819 | 0.0806 | 0.936 | 31842.0 |
| API-U03-minimax_h3_文生视频基础版API-V2 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 111.794 | 110.145 | 0.0932 | 1.082 | 31838.0 |
| API-U06-9图3音频-V5 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 93.421 | 89.097 | 0.0779 | 0.904 | 31852.0 |
| API-U06-无加速多参 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 119.445 | 115.608 | 0.0995 | 1.156 | 31834.0 |
| API-U06V9-9图3音 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 145.161 | 141.274 | 0.1210 | 1.405 | 31848.0 |
| API-U07-A | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 263.182 | 253.785 | 0.2193 | 2.547 | 31846.0 |
| API-U08 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 118.512 | 114.043 | 0.0988 | 1.147 | 31832.0 |
| API-U09-9图版API-V2 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 174.647 | 167.541 | 0.1455 | 1.690 | 31842.0 |
| API-U11-Minimax-图片音频对口型API | H3视频 | 执行失败 | — | 86.815 | 82.746 | 0.0723 | — | 17074.0 |
| API-U17-9图1视频3音频V1-api | H3视频 | 成功 | 2560×1408 / 5.167s / 带音频 | 181.024 | 177.167 | 0.1509 | 1.752 | 31832.0 |
| API-U22-9图3音 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 184.965 | 181.268 | 0.1541 | 1.790 | 31848.0 |
| API-U22-9图3音V1 | H3视频 | 成功 | 640×1120 / 5.167s / 带音频 | 119.014 | 115.526 | 0.0992 | 1.152 | 32056.0 |
| API-U30 | H3视频 | 成功 | 1280×704 / 5.167s / 带音频 | 150.017 | 146.36 | 0.1250 | 1.452 | 32068.0 |
| API-U32 | H3视频 | 成功 | 864×480 / 5.167s / 带音频 | 95.947 | 93.732 | 0.0800 | 0.928 | 31846.0 |
| API-H17-文图生视频-LTX2.3全面优化版 | LTX视频 | 成功 | 1728×960 / 5.042s / 带音频 | 244.939 | 240.664 | 0.2041 | 2.429 | 30896.0 |
| API-H28-LTX2.3-高动态图生视频 | LTX视频 | 成功 | 896×1664 / 4.834s / 带音频 | 196.489 | 188.552 | 0.1637 | 2.032 | 31006.0 |
| API-H31-ltx2.3声音-图像生成视频 | LTX视频 | 成功 | 832×448 / 9.042s / 带音频 | 197.635 | 189.155 | 0.1647 | 1.093 | 29716.0 |
| API-J11-LTX2.3高清超自然电商数字人 | LTX视频 | 成功 | 864×480 / 5.100s / 带音频 | 179.423 | 173.794 | 0.1495 | 1.759 | 31852.0 |
| API-Y08-四宫格-LTX-2.3图生视频优化版 | LTX视频 | 成功 | 864×480 / 5.042s / 带音频 | 112.868 | 102.964 | 0.0941 | 1.119 | 31836.0 |
| API-G01-图生视频-Wan2.2万相基础版 | Wan视频 | 成功 | 480×864 / 5.042s / 无音轨 | 291.284 | 286.962 | 0.2427 | 2.889 | 14394.0 |
| API-G02-首尾帧-Wan2.2首尾帧视频 | Wan视频 | 成功 | 480×864 / 5.042s / 无音轨 | 386.028 | 381.644 | 0.3217 | 3.828 | 19738.0 |
| API-G03-图生视频-Wan2.2SmoothMix | Wan视频 | 成功 | 960×1728 / 5.367s / 无音轨; 960×1728 | 235.91 | 230.509 | 0.1966 | 2.198 | 28810.0 |
| API-G10-图生视频-Wan2.2SmoothMixV2 | Wan视频 | 成功 | 480×864 / 5.063s / 无音轨; 480×864 / 5.367s / 无音轨; 960×1728 | 219.304 | 212.911 | 0.1828 | 2.043 | 29898.0 |
| API-P02-动作迁移-Wan2.2Animate角色迁移 | 动作迁移 | 成功 | 480×864 / 6.375s / 带音频; 616×864 / 6.375s / 带音频 | 206.841 | 196.505 | 0.1724 | 1.622 | 21302.0 |
| API-P07-动作迁移-Wan2.2AnimateV4 | 动作迁移 | 成功 | 480×864 / 4.000s / 带音频 | 205.147 | 194.033 | 0.1710 | 2.564 | 26646.0 |
| API-P17-动作迁移4090-48G显卡专用V8 | 动作迁移 | 执行失败 | — | 148.883 | 142.101 | 0.1241 | — | 23734.0 |
| API-A01-文生图-Qwen2512高清放大 | 图像 | 成功 | 3686×2048 | 125.521 | 115.291 | 0.1046 | — | 31918.0 |
| API-A08-洗图-Qwen二次元转真人高清放大 | 图像 | 成功 | 2048×3668 | 248.956 | 225.656 | 0.2075 | — | 31800.0 |
| API-B13-千问角色一键多角度_multiple_character_angles-v1.0 | 图像 | 成功 | 760×1368; 760×1368; 760×1368; 760×1368 | 108.032 | 101.248 | 0.0900 | — | 31236.0 |
| API-B18-Qwenimage2.1 | 图像 | 成功 | 864×480 | 48.137 | 34.024 | 0.0401 | — | 22436.0 |
| API-B20-Qwen-Image-2.1-Turbo高速编辑版 | 图像 | 成功 | 768×1376 | 80.555 | 67.285 | 0.0671 | — | 31852.0 |
| API-C16-短剧文生图专用-支持场景-角色 | 图像 | 成功 | 1942×1080 | 80.747 | 61.859 | 0.0673 | — | 27636.0 |
| API-C18-豹豹喵呜制作-白玉AIO三采超高清写真生成 | 图像 | 成功 | 1728×960 | 148.7 | 139.401 | 0.1239 | — | 31772.0 |
| API-C19-人物设定三视图zimage双采 | 图像 | 成功 | 3686×2048 | 120.979 | 109.983 | 0.1008 | — | 31880.0 |
| API-D14-分镜-Flux克莱因9B多角度多场景 | 图像 | 成功 | 1072×1920; 1072×1920; 1072×1920; 1072×1920 | 96.784 | 92.95 | 0.0807 | — | 30400.0 |
| API-D18-klein9b真人剧制造机-多图编辑 | 图像 | 成功 | 3686×2048 | 128.383 | 122.243 | 0.1070 | — | 30558.0 |
| API-D20-RAW画质重建Adonis_Workflow | 图像 | 成功 | 960×1744 | 74.76 | 65.336 | 0.0623 | — | 23386.0 |
| API-T10-Krea2做剧图像4视图 | 图像 | 成功 | 864×480 | 69.664 | 61.429 | 0.0581 | — | 21802.0 |
| API-T15-MJ风格文生图 | 图像 | 成功 | 864×480 | 45.124 | 37.511 | 0.0376 | — | 20586.0 |
| API-T4-Krea2-int8-角色设定三视图 | 图像 | 成功 | 864×480 | 91.678 | 84.59 | 0.0764 | — | 29760.0 |
| API-U00-minimax_h3提示词QWEN3.8群主版 | 提示词 | 成功 | 文本 2650 字符 | 45.146 | 41.189 | 0.0376 | — | 19542.0 |
| API-M19去字幕 | 视频后期 | 成功 | 480×864 / 5.000s / 带音频 | 117.253 | 113.377 | 0.0977 | — | 31844.0 |
| API-M20-RelayVSR视频高速超分2x | 视频后期 | 成功 | 960×1728 / 5.000s / 带音频 | 28.123 | 19.67 | 0.0234 | — | 13128.0 |
| API-Z10-专业视频补帧 | 视频后期 | 成功 | 480×864 / 5.000s / 带音频 | 30.182 | 25.093 | 0.0252 | — | 5914.0 |
| API-N2-单人声音克隆FishAudioS2pro | 语音 | 成功 | 音频 2.415s | 89.976 | 85.361 | 0.0750 | — | 26880.0 |
| API-U00-首页H3多参考 | H3视频 | 成功 | 1280×704 / 5.167s / 带音频 | 239.746 | 232.839 | 0.1998 | 2.320 | 32104.0 |
| API-U06-首页视频生成V5 | H3视频 | 成功 | 1728×960 / 5.167s / 带音频 | 101.759 | 93.328 | 0.0848 | 0.985 | 31854.0 |
| API-M02-首页画质增强 | 图像后期 | 成功 | 3413×6144 | 49.221 | 44.508 | 0.0410 | — | 12402.0 |

## 先看这些实测数值

同为约5秒镜头，各模板的采样及后处理不同，下表是成本参考，不能据此比较画质。

| 入口/配置 | 实际输出 | 请求耗时/秒 | 等效费用/元 | 线性折合60秒/元 |
|---|---|---:|---:|---:|
| API-U06-9图版API-V5 | 864×480 / 5.167s / 带音频 | 93.303 | 0.0778 | 0.903 |
| API-U06-首页视频生成V5 | 1728×960 / 5.167s / 带音频 | 101.759 | 0.0848 | 0.985 |
| API-U00-首页H3多参考 | 1280×704 / 5.167s / 带音频 | 239.746 | 0.1998 | 2.320 |
| 首页U06原生1.0MP档（首轮） | 2752×1536 / 5.167s / 带音频 | 187.557 | 0.1563 | 1.815 |

这里的1728×960和2752×1536包含工作流二采/放大；不是声明模型在该尺寸原生一次采样。连续60秒仍需分镜生成、审核和剪辑，表中只做线性换算。

## 产出文件核验

- 对71个唯一生成媒体文件执行完整解码，71个通过；视频/音频用ffmpeg逐帧/逐采样解码，图片用Pillow读取全部像素。
- 解码验证在推理计时结束后进行，不加入生成请求耗时；仍可能产生少量开机时间。
- 提示词助手输出2650字符文本；这只验证有文本返回，不评价提示词内容质量。
- Z10历史返回漏掉子目录，已按本轮目录内唯一同名文件定位真实产出并重新探测；原报告路径保留在JSON的reported_file中。
- 输入素材与临时预览不作为最终产出；每项主表只显示生成文件。
- [完整解码核验记录](../../assets/benchmarks/lichtv-2026-11-15/media-verification.json)

## 可离线查看的H3样片

- [首页U00样片](../../assets/benchmarks/lichtv-2026-11-15/samples/home-u00.mp4)：1280×704，5.167秒。
- [首页U06原生1.0MP档样片](../../assets/benchmarks/lichtv-2026-11-15/samples/home-u06-native-1mp.mp4)：2752×1536，5.167秒。
- [首页U06低分辨率档样片](../../assets/benchmarks/lichtv-2026-11-15/samples/home-u06-04mp.mp4)：1728×960，5.167秒。

样片用于人工检查画面和声音；本报告未作盲评、口型准确度评分或多镜头一致性评分。

## 服务中断与空闲租费

- 原批次运行提示词辅助工作流时连接重置，后续流程停止。该次列为服务中断，不能计为成功生成。服务日志另观察到进程被Killed、退出码137；没有足够证据将具体原因确定为GPU或容器OOM。
- 原监测中断时间：2026-11-15T04:10:22.841643+08:00；服务恢复确认：2026-11-15T12:43:48.455878+08:00。间隔约8.557小时。
- 若实例在该间隔一直按3元/小时开机，等效租费约25.671元。这是空闲/中断窗口的租费，不是视频生成费用，且已包含在整体观察窗口折算中，不能重复相加。
- 提示词首次尝试的25.506秒根据持久化START与fatal时间戳恢复，含准备/检测误差；没有完整执行历史，不给出成功推理时长。
- 已恢复同版本ComfyUI并断点续测。提示词工作流安排在独立新进程中最后补测；此前成功任务的原始历史已落盘，在线history重启后可能不再保留，但产出文件仍在。

## 首页入口与测试清单映射

首页其余六个入口的执行图（class_type和inputs）与API清单完全一致，复用对应测试结果，不重复消耗GPU。M02为独立图，另测。

| 首页模板 | 对应API工作流 | 执行图一致 |
|---|---|---|
| J11-LTX2.3高清超自然电商数字人.json | API-J11-LTX2.3高清超自然电商数字人 | 是 |
| G10-图生视频-Wan2.2SmoothMixV2.json | API-G10-图生视频-Wan2.2SmoothMixV2 | 是 |
| T4-Krea2-int8-角色设定三视图.json | API-T4-Krea2-int8-角色设定三视图 | 是 |
| D18-klein9b真人剧制造机-多图编辑.json | API-D18-klein9b真人剧制造机-多图编辑 | 是 |
| N2-单人声音克隆FishAudio S2pro.json | API-N2-单人声音克隆FishAudioS2pro | 是 |
| D14-分镜-Flux克莱因9B多角度多场景.json | API-D14-分镜-Flux克莱因9B多角度多场景 | 是 |
| M02-放大-SeedVR2+TTP高清放大.json | 新增独立测试：API-M02-首页画质增强 | 否，单独测试 |

## 失败与补测说明

| 工作流 | 首次失败原因（节选） | 最新状态 | 尝试次数 |
|---|---|---|---:|
| API-U07-A | ref_video_1 must contain at least 48 frames under the official reference policy  | 成功 | 2 |
| API-U11-Minimax-图片音频对口型API | linear(): argument 'weight' (position 2) must be Tensor, not NoneType  | 执行失败 | 1 |
| API-J11-LTX2.3高清超自然电商数字人 | Number of segment_lengths (7) must match number of local prompts (1)  | 成功 | 2 |
| API-P17-动作迁移4090-48G显卡专用V8 | Allocation on device 0 would exceed allowed memory. (out of memory) Currently allocated     : 28.69 GiB Requested               : 1.14 GiB Device limit            : 31.36 GiB Free (according to CUDA): 1.69 MiB PyTorch limit (set by user-supplied memo | 执行失败 | 1 |
| API-U00-minimax_h3提示词QWEN3.8群主版 | [Errno 104] Connection reset by peer | 成功 | 2 |

### 输入修正和故障归因

- J11：本轮统一测试提示词将七段结构改为单段，却保留了七段段长，造成不匹配；补测改为153帧单段。这是测试输入构造问题，不能据首轮失败认定原模板有缺陷。
- U07-A：面板API给未提供的视频槽位填入一帧空白视频，与T8要求至少48帧的规则冲突；补测为三个视频槽位提供有效五秒素材，模型与采样配置保持不变。
- G02：首轮尾帧为空白占位仍可执行；补充真实尾帧，主表采用完整首尾帧输入的最新结果。
- Y08：首轮通用单图不足以代表四宫格用途；补充由四个视频时刻组成的2×2参考图。
- 首页U06：原生模板用ResolutionSelector的megapixels控制分辨率，首轮保留1.0MP设置；另一个API模板的自定义宽高字段对该节点不起作用。补充改用0.4MP，并保留原生档的独立耗时与输出证据。
- U11：错误出现在TextGenerate节点（weight为None），不能据此判断H3采样器本身不可用。
- P17：本轮在WanVideoSampler发生GPU显存超限；仅说明该硬件与本轮配置组合未完成，不据此宣称所有调参方式均不可用。
- 首轮执行情况包含测试输入整形问题，不能作为产品稳定性或真实用户失败率；以逐项最后有效输入结果和完整尝试记录为准。

## 后端配置、参数与逐项证据

以下模型名称是模板引用；有旁路、选择器或封装的工作流，不保证每个引用分支都被执行。封装内部未暴露的配置明确标为未知，不根据文件名推断。模型名称和精度标签按镜像配置记录，未核验其官方命名或发行来源。所有执行框架均为当前ComfyUI服务。

### API-Z-连通测试

- 来源：`registered-api-workflow`；类别：连通测试；结果：成功。
- 实测任务编号：`5a2b1cd6-9252-403b-83f4-1e87a7887dc8`；开始UTC：`2026-11-14T18:25:28.094302+00:00`；结束UTC：`2026-11-14T18:25:34.108408+00:00`。

模板外层未列出权重文件；具体节点与设置见JSON。

采样与运行参数：

```json
[
  {
    "node": "1",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "3",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 8
  }
]
```

本轮输入覆盖：

```json
{
  "1:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "1:seconds": 5,
  "1:megapixels": 0.4
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/01-a0f50980_00001.mp4)；17588 字节。需保持本机SSH隧道及服务器在线。

### API-U06-9图版API-V5

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`f3926537-1aa7-4d4a-a2a7-4715f18570fe`；开始UTC：`2026-11-14T18:25:34.113792+00:00`；结束UTC：`2026-11-14T18:27:08.492803+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 620 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| 677 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 710 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "620",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "725",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "732",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "748",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "1315",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "1315",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "1315",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "132:value": 5,
  "664:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "665:自定义宽": 864,
  "665:自定义高": 480,
  "142:seed": 57
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/02-d23d84d3_00001-audio.mp4)；1538408 字节。需保持本机SSH隧道及服务器在线。

### API-U00-闹闹版_s

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`04b1e11d-47ab-46c2-a860-b296d20ad233`；开始UTC：`2026-11-14T18:27:08.498619+00:00`；结束UTC：`2026-11-14T18:30:03.121291+00:00`。
- 含封装节点：部分主模型、编码器或采样配置在外层不可见，不能确认全部内部配置。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 208 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "141",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "259",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  }
]
```

本轮输入覆盖：

```json
{
  "259:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "259:seconds": 5,
  "259:megapixels": 0.4
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/03-af27af66_00001-audio.mp4)；1923124 字节。需保持本机SSH隧道及服务器在线。

### API-U01-minimax_h3_基础版API

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`fcad3e61-0893-420c-bce7-f11bb22c26cf`；开始UTC：`2026-11-14T18:30:03.126501+00:00`；结束UTC：`2026-11-14T18:32:55.081324+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 127 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_int8_convrot.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |

采样与运行参数：

```json
[
  {
    "node": "123",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "res_multistep"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 25
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "127",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "130",
    "class": "CreateVideo",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "159",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "160",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "160",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "160",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "145:自定义宽": 864,
  "145:自定义高": 480,
  "146:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "147:value": 5,
  "129:noise_seed": 42
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/04-0b5a0ccf_00001_.mp4)；1609540 字节。需保持本机SSH隧道及服务器在线。

### API-U02-minimax_h3_图生视频基础版-V2

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`33967a3d-2d8c-4206-9eb2-23bceca6c109`；开始UTC：`2026-11-14T18:32:55.087559+00:00`；结束UTC：`2026-11-14T18:35:37.012036+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 128 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 129 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 136 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 142 | UNETLoader | unet_name | minimax/minimax_h3_fl2va_pruned_int8_convrot.safetensors |
| 148 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "132",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "res_multistep"
  },
  {
    "node": "133",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "133",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 25
  },
  {
    "node": "133",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "136",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "138",
    "class": "CreateVideo",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "142",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "149",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "149",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "149",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "122:自定义宽": 864,
  "122:自定义高": 480,
  "139:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "141:value": 5,
  "137:noise_seed": 66
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/05-ed58b0b2_00001_.mp4)；973411 字节。需保持本机SSH隧道及服务器在线。

### API-U03-minimax_h3_light2v-文生视频加速版API-V2

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`a609cc32-04d0-4d5a-8a82-21700dce9918`；开始UTC：`2026-11-14T18:35:37.017837+00:00`；结束UTC：`2026-11-14T18:37:14.870996+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 128 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 129 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 136 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 142 | UNETLoader | unet_name | minimax/minimax_h3_fl2va_pruned_int8_convrot.safetensors |
| 144 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "132",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "133",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "133",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 12
  },
  {
    "node": "133",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "136",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "138",
    "class": "CreateVideo",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "142",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "149",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "150",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "150",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "150",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "120:自定义宽": 864,
  "120:自定义高": 480,
  "139:prompt": "A cinematic five-second shot of an adult woman in a blue jacket, gently smiling and turning toward the camera, soft daylight, natural motion, no subtitles, no watermark.",
  "141:value": 5,
  "137:noise_seed": 65
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/06-5e93cf86_00001_.mp4)；934295 字节。需保持本机SSH隧道及服务器在线。

### API-U03-minimax_h3_文生视频基础版API-V2

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`b3b98afb-05ad-4808-88f5-3ca6b0b8896d`；开始UTC：`2026-11-14T18:37:14.877137+00:00`；结束UTC：`2026-11-14T18:39:07.751364+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 126 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 127 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 134 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 140 | UNETLoader | unet_name | minimax/minimax_h3_fl2va_pruned_int8_convrot.safetensors |
| 144 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "130",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "res_multistep"
  },
  {
    "node": "131",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "131",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 25
  },
  {
    "node": "131",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "134",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "140",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "145",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "149",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "151",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "151",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "151",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "120:自定义宽": 864,
  "120:自定义高": 480,
  "137:prompt": "A cinematic five-second shot of an adult woman in a blue jacket, gently smiling and turning toward the camera, soft daylight, natural motion, no subtitles, no watermark.",
  "139:value": 5,
  "135:noise_seed": 64
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/07-9b9f986d_00001-audio.mp4)；1981983 字节。需保持本机SSH隧道及服务器在线。

### API-U06-9图3音频-V5

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`a018719c-b986-4b24-8aad-9b5b5015a970`；开始UTC：`2026-11-14T18:39:07.757891+00:00`；结束UTC：`2026-11-14T18:40:44.209855+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 620 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| 710 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "620",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "725",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "er_sde"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "732",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "748",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "1315",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "1315",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "1315",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "132:value": 5,
  "664:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "665:自定义宽": 864,
  "665:自定义高": 480,
  "142:seed": 58
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/08-ec75c3f5_00001-audio.mp4)；1536139 字节。需保持本机SSH隧道及服务器在线。

### API-U06-无加速多参

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`c27aed70-dbd2-4f3a-951d-19ee42f954f4`；开始UTC：`2026-11-14T18:40:44.215062+00:00`；结束UTC：`2026-11-14T18:42:44.738966+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_int8_convrot.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 620 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| 677 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "620",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "725",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 28
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "732",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "748",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  }
]
```

本轮输入覆盖：

```json
{
  "132:value": 5,
  "664:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "665:megapixels": 0.4,
  "142:seed": 52
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/09-85de2686_00001-audio.mp4)；856365 字节。需保持本机SSH隧道及服务器在线。

### API-U06V9-9图3音

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`33ecc8cf-59bb-414b-a848-0f27dab70dfc`；开始UTC：`2026-11-14T18:42:44.744250+00:00`；结束UTC：`2026-11-14T18:45:10.989229+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 677 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 3939 | ZealmanH3ModelLoader | unet_name | minimax/Minimax-h3_Singularity_ref2va_v1.3_int8.safetensors |
| 3939 | ZealmanH3ModelLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |
| 3939 | ZealmanH3ModelLoader | video_vae | minimax_h3_video_vae_int8_convrot.safetensors |
| 3939 | ZealmanH3ModelLoader | audio_vae | minimax_h3_audio_vae_fp32.safetensors |
| 3951 | SenseNovaH3DistilledBridge | distilled_adapter | t8_compat/MiniMaxH3_SemanticBridge_v1_T8_Compat.safetensors |

采样与运行参数：

```json
[
  {
    "node": "732",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "3892",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "3939",
    "class": "ZealmanH3ModelLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "3939",
    "class": "ZealmanH3ModelLoader",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "3954",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "er_sde"
  },
  {
    "node": "3967",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "3967",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "3967",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "3974",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 1
  },
  {
    "node": "3974",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.7
  },
  {
    "node": "3974",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "3892:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "3892:seconds": 5,
  "3892:megapixels": 0.4,
  "3978:noise_seed": 51
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/10-a7f51a73_00001-audio.mp4)；1629855 字节。需保持本机SSH隧道及服务器在线。

### API-U07-A

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`0412cb91-f40f-4123-bb73-ba9a784241c4`；开始UTC：`2026-11-15T05:06:52.866328+00:00`；结束UTC：`2026-11-15T05:11:17.121978+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 316 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 318 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 319 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 327 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_turbo_4步加速_comfyui.safetensors |
| 332 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_int8_convrot.safetensors |

采样与运行参数：

```json
[
  {
    "node": "316",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "328",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "331",
    "class": "MiniMaxH3MultiRateSamplerEXPT8",
    "parameter": "shift_video",
    "value": 12
  },
  {
    "node": "331",
    "class": "MiniMaxH3MultiRateSamplerEXPT8",
    "parameter": "shift_audio",
    "value": 3
  },
  {
    "node": "332",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "370",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 0
  },
  {
    "node": "370",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "370",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "312:value": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "323:value": 5,
  "374:自定义宽": 864,
  "374:自定义高": 480,
  "321:noise_seed": 63,
  "329:seed": 63
}
```

- 共2次尝试，所有尝试等效费用合计0.2276元。下列主结果采用最后一次记录；历史失败与实际输入见JSON的attempts字段。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/01-ec094388_00001-audio.mp4)；1151753 字节。需保持本机SSH隧道及服务器在线。

### API-U08

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`e2ed03a3-93fd-4c82-b10b-f4b922d01615`；开始UTC：`2026-11-14T18:45:21.954045+00:00`；结束UTC：`2026-11-14T18:47:21.555796+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 2 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |
| 3 | VAELoader | vae_name | minimax_h3_video_vae_int8_convrot.safetensors |
| 4 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 24 | DiffusionModelLoaderKJ | model_name | minimax/minimax_h3_fused_refdelta_r1024_turbo8_mystic07_int8_convrot.safetensors |
| 82 | MMH3LatentUpscaleWithModelParams | model_name | minimax_h3_latent_upscaler_3d_fp16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "2",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "5",
    "class": "MiniMaxH3SigmaShift",
    "parameter": "shift_video",
    "value": 12
  },
  {
    "node": "5",
    "class": "MiniMaxH3SigmaShift",
    "parameter": "shift_audio",
    "value": 3
  },
  {
    "node": "12",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "24",
    "class": "DiffusionModelLoaderKJ",
    "parameter": "model_name",
    "value": "minimax/minimax_h3_fused_refdelta_r1024_turbo8_mystic07_int8_convrot.safetensors"
  },
  {
    "node": "24",
    "class": "DiffusionModelLoaderKJ",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "82",
    "class": "MMH3LatentUpscaleWithModelParams",
    "parameter": "model_name",
    "value": "minimax_h3_latent_upscaler_3d_fp16.safetensors"
  },
  {
    "node": "82",
    "class": "MMH3LatentUpscaleWithModelParams",
    "parameter": "device",
    "value": "cuda"
  },
  {
    "node": "82",
    "class": "MMH3LatentUpscaleWithModelParams",
    "parameter": "precision",
    "value": "fp16"
  },
  {
    "node": "83",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "83",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 1
  },
  {
    "node": "83",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 0.2
  },
  {
    "node": "84",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "sa_solver"
  },
  {
    "node": "86",
    "class": "MMH3UltimateUpscale",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "124",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  }
]
```

本轮输入覆盖：

```json
{
  "7:megapixels": 0.4,
  "8:value": 5,
  "81:megapixels": 0.4,
  "103:value": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "11:noise_seed": 56,
  "85:noise_seed": 56
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/12-d0cf03ac_00001-audio.mp4)；1745279 字节。需保持本机SSH隧道及服务器在线。

### API-U09-9图版API-V2

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`9e7d4b0a-33ae-4a6a-8ce0-ece36c97dd61`；开始UTC：`2026-11-14T18:47:21.561901+00:00`；结束UTC：`2026-11-14T18:50:17.285026+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_int8_convrot.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 127 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_int8_convrot.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |
| 306 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_pruned_w4a8_mixed.safetensors |
| 310 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors |
| 322 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "123",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "127",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "168",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "213",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "223",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "223",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 0.2
  },
  {
    "node": "224",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "res_multistep"
  },
  {
    "node": "304",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "306",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "334",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "334",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "334",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  },
  {
    "node": "335",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "335",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "335",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "132:value": 5,
  "138:value": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "320:megapixels": 0.4,
  "321:megapixels": 0.4,
  "129:noise_seed": 62
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/13-f7cf86a4_00001-audio.mp4)；1346523 字节。需保持本机SSH隧道及服务器在线。

### API-U11-Minimax-图片音频对口型API

- 来源：`registered-api-workflow`；类别：H3视频；结果：执行失败。
- 实测任务编号：`cf6a738d-e177-4b63-9381-815d0a7d174d`；开始UTC：`2026-11-14T18:50:17.291984+00:00`；结束UTC：`2026-11-14T18:51:45.113450+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 127 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |
| 181 | CLIPLoader | clip_name | gemma4_e4b_it_fp8_scaled.safetensors |
| 200 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors |
| 201 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 225 | ZealmanLLM_ModelLoader | 主模型 | Qwen3.8-27B-Q4_K_M.gguf |
| 225 | ZealmanLLM_ModelLoader | 视觉投影mmproj | Qwen3.8-mmproj-BF16.gguf |

采样与运行参数：

```json
[
  {
    "node": "123",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "127",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "181",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "183",
    "class": "DenoAudioTranscript",
    "parameter": "model",
    "value": "large-v3"
  },
  {
    "node": "198",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "216",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "232",
    "class": "ZealmanH3LoadImageToRefImages",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "234",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "234",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "234",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  }
]
```

本轮输入覆盖：

```json
{
  "155:duration": 5,
  "202:自定义宽": 864,
  "202:自定义高": 480,
  "129:noise_seed": 61,
  "226:seed": 61
}
```

实测错误（节选；失败不等于成功出片）：

```json
[
  {
    "prompt_id": "cf6a738d-e177-4b63-9381-815d0a7d174d",
    "node_id": "182",
    "node_type": "TextGenerate",
    "executed": [
      "128",
      "129",
      "225",
      "131",
      "181",
      "119",
      "233",
      "187",
      "120",
      "202",
      "155",
      "232",
      "183",
      "123"
    ],
    "exception_message": "linear(): argument 'weight' (position 2) must be Tensor, not NoneType\n",
    "exception_type": "TypeError",
    "traceback": [
      "  File \"/root/ComfyUI/execution.py\", line 556, in execute\n    output_data, output_ui, has_subgraph, has_pending_tasks = await get_output_data(prompt_id, unique_id, obj, input_data_all, execution_block_cb=execution_block_cb, pre_execute_cb=pre_execute_cb, v3_data=v3_data)\n                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/execution.py\", line 353, in get_output_data\n    return_values = await _async_map_node_over_list(prompt_id, unique_id, obj, input_data_all, obj.FUNCTION, allow_interrupt=True, execution_block_cb=execution_block_cb, pre_execute_cb=pre_execute_cb, v3_data=v3_data)\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/execution.py\", line 327, in _async_map_node_over_list\n    await process_inputs(input_dict, i)\n",
      "  File \"/root/ComfyUI/execution.py\", line 315, in process_inputs\n    result = f(**inputs)\n             ^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy_api/internal/__init__.py\", line 149, in wrapped_func\n    return method(locked_class, **inputs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy_api/latest/_io.py\", line 2219, in EXECUTE_NORMALIZED\n    to_return = cls.execute(*args, **kwargs)\n                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy_extras/nodes_textgen.py\", line 74, in execute\n    generated_ids = clip.generate(\n                    ^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/sd.py\", line 489, in generate\n    return self.cond_stage_model.generate(tokens, do_sample=do_sample, max_length=max_length, temperature=temperature, top_k=top_k, top_p=top_p, min_p=min_p, repetition_penalty=repetition_penalty, seed=seed, presence_penalty=presence_penalty, mtp=mtp)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/sd1_clip.py\", line 750, in generate\n    return getattr(self, self.clip).generate(tokens, do_sample=do_sample, max_length=max_length, temperature=temperature, top_k=top_k, top_p=top_p, min_p=min_p, repetition_penalty=repetition_penalty, seed=seed, presence_penalty=presence_penalty, mtp=mtp)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/text_encoders/gemma4.py\", line 1698, in generate\n    return self.transformer.generate(embeds, do_sample, max_length, temperature, top_k, top_p, min_p, repetition_penalty, seed, initial_tokens=initial_token_ids[0], presence_penalty=presence_penalty, initial_input_ids=input_ids, embeds_info=embeds_info)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/text_encoders/llama.py\", line 1266, in generate\n    x, _, past_key_values = self.model.forward(None, embeds=embeds, attention_mask=None, past_key_values=past_key_values, input_ids=current_input_ids, position_ids=position_ids, **extra, embeds_info=(embeds_info if step == 0 else None))\n                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/text_encoders/gemma4.py\", line 606, in forward\n    comfy.model_prefetch.prefetch_queue_pop(\n",
      "  File \"/root/ComfyUI/comfy/model_prefetch.py\", line 329, in prefetch_queue_pop\n    core()\n",
      "  File \"/root/ComfyUI/comfy/text_encoders/gemma4.py\", line 599, in core\n    output, current_kv, shareable_kv = layer(x=x, attention_mask=layer_mask, freqs_cis=freqs_cis, past_key_value=past_kv, **layer_kwargs)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1778, in _wrapped_call_impl\n    return self._call_impl(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1789, in _call_impl\n    return forward_call(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/text_encoders/gemma4.py\", line 349, in forward\n    x = self.mlp(x)\n        ^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1778, in _wrapped_call_impl\n    return self._call_impl(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1789, in _call_impl\n    return forward_call(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/text_encoders/llama.py\", line 814, in forward\n    return self.down_proj(self.activation(self.gate_proj(x)) * self.up_proj(x))\n                                          ^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1778, in _wrapped_call_impl\n    return self._call_impl(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1789, in _call_impl\n    return forward_call(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/ops.py\", line 1661, in forward\n    output = self.forward_comfy_cast_weights(\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/ops.py\", line 1592, in forward_comfy_cast_weights\n    return self._forward(input, weight, bias)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/comfy/ops.py\", line 1573, in _forward\n    return torch.nn.functional.linear(input, weight, bias)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n"
    ],
    "timestamp": 1794682301102
  }
]
```

### API-U17-9图1视频3音频V1-api

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`7264b507-3f10-40c5-8090-8912c43a18b6`；开始UTC：`2026-11-14T18:51:45.119631+00:00`；结束UTC：`2026-11-14T18:54:47.260176+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 150 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors |
| 226 | MinimaxH3LatentUpscaler3D | model_name | minimax_h3_latent_upscaler_3d_bf16.safetensors |
| 233 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_fl2v_turbo_4step_v1.1_768p_comfyui_bf16.safetensors |
| 236 | UNETLoader | unet_name | minimax/minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors |
| 251 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 252 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "123",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "res_multistep"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "124",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "179",
    "class": "CreateVideo",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "226",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "model_name",
    "value": "minimax_h3_latent_upscaler_3d_bf16.safetensors"
  },
  {
    "node": "226",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "device",
    "value": "cuda"
  },
  {
    "node": "226",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "228",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "pytorch attention"
  },
  {
    "node": "232",
    "class": "ExtendIntermediateSigmas",
    "parameter": "steps",
    "value": 1
  },
  {
    "node": "232",
    "class": "ExtendIntermediateSigmas",
    "parameter": "start_at_sigma",
    "value": 0.6500000000000001
  },
  {
    "node": "232",
    "class": "ExtendIntermediateSigmas",
    "parameter": "end_at_sigma",
    "value": 0
  },
  {
    "node": "236",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "262",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  }
]
```

本轮输入覆盖：

```json
{
  "115:megapixels": 0.4,
  "132:value": 5,
  "129:noise_seed": 60
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/15-bd71e52f_00001_.mp4)；16155285 字节。需保持本机SSH隧道及服务器在线。

### API-U22-9图3音

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`604c8950-ed83-4b50-8619-6c441ac53b69`；开始UTC：`2026-11-14T18:54:47.266331+00:00`；结束UTC：`2026-11-14T18:57:54.030397+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 329 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 397 | SelfLiftH3Sampler | upscaler_model | h3_upscaler_lms_v0.1.safetensors |
| 411 | ZealmanH3ModelLoader | unet_name | minimax/minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors |
| 411 | ZealmanH3ModelLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 411 | ZealmanH3ModelLoader | video_vae | minimax_h3_video_vae_int8_convrot.safetensors |
| 411 | ZealmanH3ModelLoader | audio_vae | minimax_h3_audio_vae_fp32.safetensors |

采样与运行参数：

```json
[
  {
    "node": "255",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "261",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "261",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 10
  },
  {
    "node": "261",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "333",
    "class": "MiniMaxH3SigmaShift",
    "parameter": "shift_video",
    "value": 12
  },
  {
    "node": "333",
    "class": "MiniMaxH3SigmaShift",
    "parameter": "shift_audio",
    "value": 3.0000000000000004
  },
  {
    "node": "364",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "397",
    "class": "SelfLiftH3Sampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "403",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "411",
    "class": "ZealmanH3ModelLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "411",
    "class": "ZealmanH3ModelLoader",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  }
]
```

本轮输入覆盖：

```json
{
  "403:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "403:seconds": 5,
  "403:megapixels": 0.4,
  "397:seed": 50
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/16-548cd308_00001-audio.mp4)；1445066 字节。需保持本机SSH隧道及服务器在线。

### API-U22-9图3音V1

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`14bdfc7a-376e-4932-b504-05aba5a67b70`；开始UTC：`2026-11-14T18:57:54.035833+00:00`；结束UTC：`2026-11-14T18:59:54.128415+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 36 | VAELoader | vae_name | minimax_h3_video_vae_int8_convrot.safetensors |
| 37 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 38 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 53 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors |
| 128 | LoraLoaderModelOnly | lora_name | minimax/MysticXXX_MMH3-V1.safetensors |
| 192 | UNETLoader | unet_name | minimax/minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors |
| 292 | MinimaxH3LatentUpscaler3D | model_name | minimax_h3_latent_upscaler_3d_fp16.safetensors |
| 295 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "38",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "192",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "214",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "255",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "261",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "261",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 12
  },
  {
    "node": "261",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "290",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "292",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "model_name",
    "value": "minimax_h3_latent_upscaler_3d_fp16.safetensors"
  },
  {
    "node": "292",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "device",
    "value": "cuda"
  },
  {
    "node": "292",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "precision",
    "value": "fp16"
  },
  {
    "node": "294",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  }
]
```

本轮输入覆盖：

```json
{
  "290:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "290:seconds": 5,
  "290:megapixels": 0.4,
  "256:noise_seed": 49
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/17-bedd0d56_00001-audio.mp4)；2715513 字节。需保持本机SSH隧道及服务器在线。

### API-U30

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`d3591efd-7b90-498e-9f6f-b214eaa9266c`；开始UTC：`2026-11-14T18:59:54.134489+00:00`；结束UTC：`2026-11-14T19:02:25.242969+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 124 | MinimaxH3LatentUpscaler3D | model_name | minimax_h3_latent_upscaler_3d_bf16.safetensors |
| 208 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 214 | SenseNovaH3DistilledBridge | distilled_adapter | t8_compat/MiniMaxH3_SemanticBridge_v1_T8_Compat.safetensors |
| 301 | ZealmanH3ModelLoader | unet_name | minimax/Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors |
| 301 | ZealmanH3ModelLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |
| 301 | ZealmanH3ModelLoader | video_vae | minimax_h3_video_vae_int8_convrot.safetensors |
| 301 | ZealmanH3ModelLoader | audio_vae | minimax_h3_audio_vae_fp32.safetensors |

采样与运行参数：

```json
[
  {
    "node": "58",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "71",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "71",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 6
  },
  {
    "node": "71",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "94",
    "class": "ExtendIntermediateSigmas",
    "parameter": "steps",
    "value": 2
  },
  {
    "node": "94",
    "class": "ExtendIntermediateSigmas",
    "parameter": "start_at_sigma",
    "value": 1.0000000000000002
  },
  {
    "node": "94",
    "class": "ExtendIntermediateSigmas",
    "parameter": "end_at_sigma",
    "value": 0
  },
  {
    "node": "124",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "model_name",
    "value": "minimax_h3_latent_upscaler_3d_bf16.safetensors"
  },
  {
    "node": "124",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "device",
    "value": "cuda"
  },
  {
    "node": "124",
    "class": "MinimaxH3LatentUpscaler3D",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "141",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "259",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  },
  {
    "node": "301",
    "class": "ZealmanH3ModelLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "301",
    "class": "ZealmanH3ModelLoader",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  }
]
```

本轮输入覆盖：

```json
{
  "259:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "259:seconds": 5,
  "259:megapixels": 0.4,
  "63:noise_seed": 55
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/18-d6251ab5_00001-audio.mp4)；2310239 字节。需保持本机SSH隧道及服务器在线。

### API-U32

- 来源：`registered-api-workflow`；类别：H3视频；结果：成功。
- 实测任务编号：`33efb34e-4fbd-4c56-9846-84f16c2c7476`；开始UTC：`2026-11-14T19:02:25.248526+00:00`；结束UTC：`2026-11-14T19:04:02.268373+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 1 | VAELoader | vae_name | minimax_h3_video_vae_fp16.safetensors |
| 2 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 3 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_int8_convrot.safetensors |
| 4 | UNETLoader | unet_name | minimax/minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors |
| 5 | LoraLoaderBypassModelOnly | lora_name | minimax/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors |
| 45 | LoraLoaderModelOnly | lora_name | minimax/Motion_Repair.safetensors |
| 47 | LoraLoaderModelOnly | lora_name | minimax/Bunny_weapon_combatV1.safetensors |
| 79 | SelfLiftH3Sampler | upscaler_model | minimax_h3_latent_upscaler_3d_bf16.safetensors |
| 83 | LoraLoaderModelOnly | lora_name | minimax/H3_Combat_V2.safetensors |

采样与运行参数：

```json
[
  {
    "node": "3",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "4",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "75",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "76",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "76",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "76",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "77",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 1
  },
  {
    "node": "77",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.7
  },
  {
    "node": "77",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0
  },
  {
    "node": "79",
    "class": "SelfLiftH3Sampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "89",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  }
]
```

本轮输入覆盖：

```json
{
  "27:value": 5,
  "29:megapixels": 0.4,
  "88:value": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "79:seed": 54
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/19-4cafe985_00001-audio.mp4)；1499959 字节。需保持本机SSH隧道及服务器在线。

### API-H17-文图生视频-LTX2.3全面优化版

- 来源：`registered-api-workflow`；类别：LTX视频；结果：成功。
- 实测任务编号：`38d0d55c-842d-4b14-90e1-09923b235901`；开始UTC：`2026-11-14T19:04:02.274025+00:00`；结束UTC：`2026-11-14T19:08:09.670258+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 3940 | CheckpointLoaderSimple | ckpt_name | ltx-2.3-22b-dev.safetensors |
| 4010 | LTXVAudioVAELoader | ckpt_name | ltx-2.3-22b-dev.safetensors |
| 4922 | LoraLoaderModelOnly | lora_name | Ltx/ltx-2.3-22b-distilled-lora-384.safetensors |
| 4974 | LatentUpscaleModelLoader | model_name | ltx-2.3-spatial-upscaler-x2-1.0.safetensors |
| 4982 | LTXAVTextEncoderLoader | text_encoder | gemma_3_12B_it_fp8_e4m3fn.safetensors |
| 4982 | LTXAVTextEncoderLoader | ckpt_name | ltx-2.3-22b-dev.safetensors |

采样与运行参数：

```json
[
  {
    "node": "3059",
    "class": "EmptyLTXVLatentVideo",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "3980",
    "class": "LTXVEmptyLatentAudio",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "4828",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "4831",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_ancestral_cfg_pp"
  },
  {
    "node": "4964",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "4974",
    "class": "LatentUpscaleModelLoader",
    "parameter": "model_name",
    "value": "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
  },
  {
    "node": "4976",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_cfg_pp"
  },
  {
    "node": "4982",
    "class": "LTXAVTextEncoderLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "5011",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  }
]
```

本轮输入覆盖：

```json
{
  "5013:text": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "5018:value": 864,
  "5020:value": 480,
  "5046:value": 5,
  "4832:noise_seed": 77,
  "4967:noise_seed": 77,
  "5043:seed": 77
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/20-0b54a206_00001-audio.mp4)；1727098 字节。需保持本机SSH隧道及服务器在线。

### API-H28-LTX2.3-高动态图生视频

- 来源：`registered-api-workflow`；类别：LTX视频；结果：成功。
- 实测任务编号：`ed078303-5229-4d1b-a38d-4b45a5550f07`；开始UTC：`2026-11-14T19:08:09.675182+00:00`；结束UTC：`2026-11-14T19:11:27.335824+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 313 | LatentUpscaleModelLoader | model_name | ltx-2.3-spatial-upscaler-x2-1.0.safetensors |
| 318 | UNETLoader | unet_name | Ltx/ltx-2.3-22b-distilled_transformer_only_fp8_input_scaled_v3.safetensors |
| 319 | VAELoaderKJ | vae_name | LTX23_video_vae_bf16.safetensors |
| 320 | VAELoaderKJ | vae_name | LTX23_audio_vae_bf16.safetensors |
| 324 | DualCLIPLoader | clip_name1 | gemma_3_12B_it_fp8_e4m3fn.safetensors |
| 324 | DualCLIPLoader | clip_name2 | ltx-2.3_text_projection_bf16.safetensors |
| 436 | LoraLoader | lora_name | gemma-3-12b-it-abliterated_heretic_lora_rank64_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "279",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_cfg_pp"
  },
  {
    "node": "282",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "291",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_ancestral_cfg_pp"
  },
  {
    "node": "295",
    "class": "EmptyLTXVLatentVideo",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "307",
    "class": "LTXVEmptyLatentAudio",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "313",
    "class": "LatentUpscaleModelLoader",
    "parameter": "model_name",
    "value": "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
  },
  {
    "node": "316",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "318",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "319",
    "class": "VAELoaderKJ",
    "parameter": "device",
    "value": "main_device"
  },
  {
    "node": "319",
    "class": "VAELoaderKJ",
    "parameter": "weight_dtype",
    "value": "bf16"
  },
  {
    "node": "320",
    "class": "VAELoaderKJ",
    "parameter": "device",
    "value": "main_device"
  },
  {
    "node": "320",
    "class": "VAELoaderKJ",
    "parameter": "weight_dtype",
    "value": "bf16"
  },
  {
    "node": "324",
    "class": "DualCLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "334",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "441",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_cfg_pp"
  },
  {
    "node": "445",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "475:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "457:Number": 480,
  "459:Number": 864,
  "467:Number": "5",
  "274:noise_seed": 76,
  "275:noise_seed": 76,
  "440:noise_seed": 76
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/21-45184952_00001-audio.mp4)；2498411 字节。需保持本机SSH隧道及服务器在线。

### API-H31-ltx2.3声音-图像生成视频

- 来源：`registered-api-workflow`；类别：LTX视频；结果：成功。
- 实测任务编号：`e36fdd35-8dc0-4d1d-aae9-370edd30868c`；开始UTC：`2026-11-14T19:11:27.341593+00:00`；结束UTC：`2026-11-14T19:14:46.047377+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 370 | LTXVAudioVAELoader | ckpt_name | ltx-2.3-22b-dev-fp8.safetensors |
| 382 | LatentUpscaleModelLoader | model_name | ltx-2.3-spatial-upscaler-x2-1.1.safetensors |
| 383 | LoraLoaderModelOnly | lora_name | Ltx/ltx-2.3-22b-distilled-lora-384.safetensors |
| 384 | CheckpointLoaderSimple | ckpt_name | ltx-2.3-22b-dev-fp8.safetensors |
| 385 | LTXAVTextEncoderLoader | text_encoder | gemma_3_12B_it_fp4_mixed.safetensors |
| 385 | LTXAVTextEncoderLoader | ckpt_name | ltx-2.3-22b-dev-fp8.safetensors |

采样与运行参数：

```json
[
  {
    "node": "348",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_cfg_pp"
  },
  {
    "node": "350",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "355",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_ancestral_cfg_pp"
  },
  {
    "node": "365",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "376",
    "class": "EmptyLTXVLatentVideo",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "382",
    "class": "LatentUpscaleModelLoader",
    "parameter": "model_name",
    "value": "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
  },
  {
    "node": "385",
    "class": "LTXAVTextEncoderLoader",
    "parameter": "device",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "368:value": 864,
  "377:value": 480,
  "393:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "345:noise_seed": 75,
  "346:noise_seed": 75
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/22-6a5550d8_00001_.mp4)；1572773 字节。需保持本机SSH隧道及服务器在线。

### API-J11-LTX2.3高清超自然电商数字人

- 来源：`registered-api-workflow`；类别：LTX视频；结果：成功。
- 实测任务编号：`6f040930-47b2-423c-8945-441320ddedc3`；开始UTC：`2026-11-15T05:03:51.974321+00:00`；结束UTC：`2026-11-15T05:06:52.678932+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 1 | DiffusionModelLoaderKJ | model_name | Ltx/ltx-2.3-22b-distilled-1.1_transformer_only_fp8_scaled.safetensors |
| 2 | LoraLoaderModelOnly | lora_name | Ltx/Ltx2.3-Licon-VBVR-I2V-240K-R32.safetensors |
| 8 | DualCLIPLoader | clip_name1 | gemma_3_12B_it_fp8_e4m3fn.safetensors |
| 8 | DualCLIPLoader | clip_name2 | ltx-2.3_text_projection_bf16.safetensors |
| 10 | VAELoaderKJ | vae_name | LTX23_audio_vae_bf16.safetensors |
| 11 | VAELoaderKJ | vae_name | LTX23_video_vae_bf16.safetensors |
| 51 | MelBandRoFormerModelLoader | model_name | MelRoFormer/MelBandRoformer_fp32.safetensors |

采样与运行参数：

```json
[
  {
    "node": "1",
    "class": "DiffusionModelLoaderKJ",
    "parameter": "model_name",
    "value": "Ltx/ltx-2.3-22b-distilled-1.1_transformer_only_fp8_scaled.safetensors"
  },
  {
    "node": "1",
    "class": "DiffusionModelLoaderKJ",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "8",
    "class": "DualCLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "10",
    "class": "VAELoaderKJ",
    "parameter": "device",
    "value": "main_device"
  },
  {
    "node": "10",
    "class": "VAELoaderKJ",
    "parameter": "weight_dtype",
    "value": "bf16"
  },
  {
    "node": "11",
    "class": "VAELoaderKJ",
    "parameter": "device",
    "value": "main_device"
  },
  {
    "node": "11",
    "class": "VAELoaderKJ",
    "parameter": "weight_dtype",
    "value": "bf16"
  },
  {
    "node": "15",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "51",
    "class": "MelBandRoFormerModelLoader",
    "parameter": "model_name",
    "value": "MelRoFormer/MelBandRoformer_fp32.safetensors"
  },
  {
    "node": "77",
    "class": "EmptyLTXVLatentVideo",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "91",
    "class": "SamplerCustom",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "98",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_ancestral_cfg_pp"
  }
]
```

本轮输入覆盖：

```json
{
  "167:Number": 864,
  "168:Number": 480,
  "187:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "188:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "91:noise_seed": 74,
  "189:prompt": "153"
}
```

- 共2次尝试，所有尝试等效费用合计0.1812元。下列主结果采用最后一次记录；历史失败与实际输入见JSON的attempts字段。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/01-65f7b66f_00001-audio.mp4)；905309 字节。需保持本机SSH隧道及服务器在线。

### API-Y08-四宫格-LTX-2.3图生视频优化版

- 来源：`registered-api-workflow`；类别：LTX视频；结果：成功。
- 实测任务编号：`d72736c7-8635-4bc2-a8a5-ae7a817ee263`；开始UTC：`2026-11-15T05:11:17.248227+00:00`；结束UTC：`2026-11-15T05:13:11.195619+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 14 | LatentUpscaleModelLoader | model_name | ltx-2.3-spatial-upscaler-x2-1.0.safetensors |
| 53 | DualCLIPLoader | clip_name1 | gemma_3_12B_it_fp8_e4m3fn.safetensors |
| 53 | DualCLIPLoader | clip_name2 | ltx-2.3_text_projection_bf16.safetensors |
| 56 | VAELoader | vae_name | LTX23_video_vae_bf16.safetensors |
| 60 | VAELoaderKJ | vae_name | LTX23_audio_vae_bf16.safetensors |
| 151 | UNETLoader | unet_name | Ltx/ltx-2.3-22b-distilled-1.1_transformer_only_fp8_scaled.safetensors |

采样与运行参数：

```json
[
  {
    "node": "14",
    "class": "LatentUpscaleModelLoader",
    "parameter": "model_name",
    "value": "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
  },
  {
    "node": "30",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_ancestral_cfg_pp"
  },
  {
    "node": "32",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "53",
    "class": "DualCLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "60",
    "class": "VAELoaderKJ",
    "parameter": "device",
    "value": "main_device"
  },
  {
    "node": "60",
    "class": "VAELoaderKJ",
    "parameter": "weight_dtype",
    "value": "bf16"
  },
  {
    "node": "98",
    "class": "EmptyLTXVLatentVideo",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "100",
    "class": "LTXVEmptyLatentAudio",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "113",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "115",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "116",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "120",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "151",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "71:text": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "150:custom_width": 864,
  "150:custom_height": 480,
  "222:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "223:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "136:value": 5,
  "37:noise_seed": 59
}
```

- 共2次尝试，所有尝试等效费用合计0.2343元。下列主结果采用最后一次记录；历史失败与实际输入见JSON的attempts字段。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/01-acbf254d_00001-audio.mp4)；1132692 字节。需保持本机SSH隧道及服务器在线。

### API-G01-图生视频-Wan2.2万相基础版

- 来源：`registered-api-workflow`；类别：Wan视频；结果：成功。
- 实测任务编号：`cda7c5aa-7471-4706-93ac-e960d671ee30`；开始UTC：`2026-11-14T19:18:14.527707+00:00`；结束UTC：`2026-11-14T19:23:07.084565+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 121 | WanVideoModelLoader | model | Wan/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors |
| 122 | WanVideoModelLoader | model | Wan/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors |
| 123 | WanVideoLoraSelect | lora | Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors |
| 124 | WanVideoVAELoader | model_name | wan_2.1_vae.safetensors |
| 125 | LoadWanVideoT5TextEncoder | model_name | umt5-xxl-enc-fp8_e4m3fn.safetensors |
| 159 | WanVideoLoraSelect | lora | Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "121",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
  },
  {
    "node": "121",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "sageattn"
  },
  {
    "node": "122",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
  },
  {
    "node": "122",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "sageattn"
  },
  {
    "node": "124",
    "class": "WanVideoVAELoader",
    "parameter": "model_name",
    "value": "wan_2.1_vae.safetensors"
  },
  {
    "node": "124",
    "class": "WanVideoVAELoader",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "125",
    "class": "LoadWanVideoT5TextEncoder",
    "parameter": "model_name",
    "value": "umt5-xxl-enc-fp8_e4m3fn.safetensors"
  },
  {
    "node": "125",
    "class": "LoadWanVideoT5TextEncoder",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "126",
    "class": "WanVideoBlockSwap",
    "parameter": "blocks_to_swap",
    "value": 40
  },
  {
    "node": "130",
    "class": "WanVideoTextEncode",
    "parameter": "device",
    "value": "gpu"
  },
  {
    "node": "132",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 8
  },
  {
    "node": "132",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "unipc"
  },
  {
    "node": "142",
    "class": "WanVideoSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "142",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 8
  },
  {
    "node": "142",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "unipc"
  },
  {
    "node": "150",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "156",
    "class": "WanVideoBlockSwap",
    "parameter": "blocks_to_swap",
    "value": 20
  }
]
```

本轮输入覆盖：

```json
{
  "119:text": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "144:value": 864,
  "153:Number": "5",
  "132:seed": 81,
  "142:seed": 81
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/25-afbd7d8d_00001.mp4)；994470 字节。需保持本机SSH隧道及服务器在线。

### API-G02-首尾帧-Wan2.2首尾帧视频

- 来源：`registered-api-workflow`；类别：Wan视频；结果：成功。
- 实测任务编号：`19c11da9-3735-40f5-9174-3b18e05a438b`；开始UTC：`2026-11-15T04:57:24.746296+00:00`；结束UTC：`2026-11-15T05:03:51.846532+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 121 | WanVideoModelLoader | model | Wan/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors |
| 122 | WanVideoModelLoader | model | Wan/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors |
| 123 | WanVideoLoraSelect | lora | Lightx2v/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank128_bf16.safetensors |
| 124 | WanVideoVAELoader | model_name | wan_2.1_vae.safetensors |
| 125 | LoadWanVideoT5TextEncoder | model_name | umt5-xxl-enc-fp8_e4m3fn.safetensors |
| 159 | WanVideoLoraSelect | lora | Lightx2v/lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank128_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "121",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
  },
  {
    "node": "121",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "flash_attn_2"
  },
  {
    "node": "122",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
  },
  {
    "node": "122",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "flash_attn_2"
  },
  {
    "node": "124",
    "class": "WanVideoVAELoader",
    "parameter": "model_name",
    "value": "wan_2.1_vae.safetensors"
  },
  {
    "node": "124",
    "class": "WanVideoVAELoader",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "125",
    "class": "LoadWanVideoT5TextEncoder",
    "parameter": "model_name",
    "value": "umt5-xxl-enc-fp8_e4m3fn.safetensors"
  },
  {
    "node": "125",
    "class": "LoadWanVideoT5TextEncoder",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "132",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 8
  },
  {
    "node": "132",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "unipc"
  },
  {
    "node": "142",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 8
  },
  {
    "node": "142",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "unipc"
  },
  {
    "node": "150",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "156",
    "class": "WanVideoBlockSwap",
    "parameter": "blocks_to_swap",
    "value": 20
  },
  {
    "node": "170",
    "class": "WanVideoTextEncode",
    "parameter": "device",
    "value": "gpu"
  }
]
```

本轮输入覆盖：

```json
{
  "119:text": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "144:value": 864,
  "153:Number": "5",
  "142:seed": 80,
  "182:seed": 80
}
```

- 共2次尝试，所有尝试等效费用合计0.5751元。下列主结果采用最后一次记录；历史失败与实际输入见JSON的attempts字段。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/01-cc975cd1_00001.mp4)；1111898 字节。需保持本机SSH隧道及服务器在线。

### API-G03-图生视频-Wan2.2SmoothMix

- 来源：`registered-api-workflow`；类别：Wan视频；结果：成功。
- 实测任务编号：`ce5853a3-4636-4716-8f77-b5f71edfe92e`；开始UTC：`2026-11-14T19:28:12.395995+00:00`；结束UTC：`2026-11-14T19:32:09.498095+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 131:38 | CLIPLoader | clip_name | umt5_xxl_fp8_e4m3fn_scaled.safetensors |
| 131:39 | VAELoader | vae_name | wan_2.1_vae.safetensors |
| 131:37 | UNETLoader | unet_name | Wan/smoothMixWan22I2VT2V_i2vHigh.safetensors |
| 131:56 | UNETLoader | unet_name | Wan/smoothMixWan22I2VT2V_i2vLow.safetensors |
| 132:75 | RIFE VFI | ckpt_name | rife49.pth |

采样与运行参数：

```json
[
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "steps",
    "value": 6
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "cfg",
    "value": 1.5
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "sampler_name",
    "value": "euler_ancestral"
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "58",
    "class": "KSamplerAdvanced",
    "parameter": "steps",
    "value": 6
  },
  {
    "node": "58",
    "class": "KSamplerAdvanced",
    "parameter": "cfg",
    "value": 1.5
  },
  {
    "node": "58",
    "class": "KSamplerAdvanced",
    "parameter": "sampler_name",
    "value": "euler_ancestral"
  },
  {
    "node": "58",
    "class": "KSamplerAdvanced",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "77",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 30
  },
  {
    "node": "131:54",
    "class": "ModelSamplingSD3",
    "parameter": "shift",
    "value": 8.000000000000002
  },
  {
    "node": "131:38",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "131:37",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "131:56",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "131:55",
    "class": "ModelSamplingSD3",
    "parameter": "shift",
    "value": 8.000000000000002
  },
  {
    "node": "132:75",
    "class": "RIFE VFI",
    "parameter": "dtype",
    "value": "float32"
  },
  {
    "node": "132:75",
    "class": "RIFE VFI",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "132:50",
    "class": "WanImageToVideo",
    "parameter": "batch_size",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "88:value": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "116:value": 5,
  "125:value": 864,
  "58:noise_seed": 79,
  "82:seed": 79
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/27-9316d232_00001.mp4)；3031106 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/27-9316d232_00002_.png)；985931 字节。需保持本机SSH隧道及服务器在线。

### API-G10-图生视频-Wan2.2SmoothMixV2

- 来源：`registered-api-workflow`；类别：Wan视频；结果：成功。
- 实测任务编号：`aa13c7cb-58a9-4bab-bce5-cac2bc7aa3ea`；开始UTC：`2026-11-14T19:32:09.505000+00:00`；结束UTC：`2026-11-14T19:35:49.951719+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 220 | UNETLoader | unet_name | Wan/smoothMixWan2214BI2V_i2vV20High.safetensors |
| 221 | CLIPLoader | clip_name | umt5_xxl_fp8_e4m3fn_scaled.safetensors |
| 222 | VAELoader | vae_name | wan_2.1_vae.safetensors |
| 227 | UNETLoader | unet_name | Wan/smoothMixWan2214BI2V_i2vV20Low.safetensors |
| 236 | CLIPVisionLoader | clip_name | clip_vision_h.safetensors |
| 239 | LoraLoaderModelOnly | lora_name | Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank256_bf16.safetensors |
| 240 | LoraLoaderModelOnly | lora_name | Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank256_bf16.safetensors |
| 241 | RIFE VFI | ckpt_name | rife49.pth |
| 255 | LoraLoaderModelOnly | lora_name | Wan/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors |
| 256 | LoraLoaderModelOnly | lora_name | Wan/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "220",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "221",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "223",
    "class": "WanImageToVideo",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "225",
    "class": "ModelSamplingSD3",
    "parameter": "shift",
    "value": 8.000000000000002
  },
  {
    "node": "226",
    "class": "ModelSamplingSD3",
    "parameter": "shift",
    "value": 8.000000000000002
  },
  {
    "node": "227",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "228",
    "class": "KSamplerAdvanced",
    "parameter": "steps",
    "value": 6
  },
  {
    "node": "228",
    "class": "KSamplerAdvanced",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "228",
    "class": "KSamplerAdvanced",
    "parameter": "sampler_name",
    "value": "euler_ancestral"
  },
  {
    "node": "228",
    "class": "KSamplerAdvanced",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "229",
    "class": "KSamplerAdvanced",
    "parameter": "steps",
    "value": 6
  },
  {
    "node": "229",
    "class": "KSamplerAdvanced",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "229",
    "class": "KSamplerAdvanced",
    "parameter": "sampler_name",
    "value": "euler_ancestral"
  },
  {
    "node": "229",
    "class": "KSamplerAdvanced",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "230",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 16
  },
  {
    "node": "241",
    "class": "RIFE VFI",
    "parameter": "dtype",
    "value": "float32"
  },
  {
    "node": "241",
    "class": "RIFE VFI",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "242",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 30
  }
]
```

本轮输入覆盖：

```json
{
  "257:value": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "238:value": 5,
  "248:value": 864,
  "229:noise_seed": 78,
  "231:seed": 78
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/28-745cae60_00001.mp4)；1987844 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/28-745cae60_00002.mp4)；2195800 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/28-745cae60_00003_.png)；1293379 字节。需保持本机SSH隧道及服务器在线。

### API-P02-动作迁移-Wan2.2Animate角色迁移

- 来源：`registered-api-workflow`；类别：动作迁移；结果：成功。
- 实测任务编号：`031757ba-851b-46f8-b06e-1c5bbdd011a6`；开始UTC：`2026-11-14T19:35:49.958495+00:00`；结束UTC：`2026-11-14T19:39:18.047894+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 32 | WanVideoTextEncodeCached | model_name | umt5-xxl-enc-fp8_e4m3fn.safetensors |
| 43 | WanVideoVAELoader | model_name | wan_2.1_vae.safetensors |
| 50 | WanVideoModelLoader | model | Wan/Wan2.2-Animate-14B-fp8_v2.safetensors |
| 67 | WanVideoLoraSelect | lora | Wan/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors |
| 75 | WanVideoLoraSelect | lora | Wan/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors |
| 76 | WanVideoLoraSelect | lora | Wan/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors |
| 77 | WanVideoLoraSelect | lora | Wan/WanAnimate_relight_lora_fp16.safetensors |
| 78 | WanVideoLoraSelect | lora | Wan/Wan2.2-Fun-A14B-InP-LOW-HPS2.1_resized_dynamic_avg_rank_15_bf16.safetensors |
| 95 | CLIPVisionLoader | clip_name | clip_vision_h.safetensors |
| 110 | OnnxDetectionModelLoader | vitpose_model | vitpose-l-wholebody.onnx |
| 110 | OnnxDetectionModelLoader | yolo_model | yolov10m.onnx |

采样与运行参数：

```json
[
  {
    "node": "24",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "28",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "32",
    "class": "WanVideoTextEncodeCached",
    "parameter": "model_name",
    "value": "umt5-xxl-enc-fp8_e4m3fn.safetensors"
  },
  {
    "node": "32",
    "class": "WanVideoTextEncodeCached",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "32",
    "class": "WanVideoTextEncodeCached",
    "parameter": "device",
    "value": "gpu"
  },
  {
    "node": "35",
    "class": "WanVideoBlockSwap",
    "parameter": "blocks_to_swap",
    "value": 20
  },
  {
    "node": "38",
    "class": "WanVideoSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "38",
    "class": "WanVideoSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "38",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 5
  },
  {
    "node": "38",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "dpm++_sde"
  },
  {
    "node": "41",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "43",
    "class": "WanVideoVAELoader",
    "parameter": "model_name",
    "value": "wan_2.1_vae.safetensors"
  },
  {
    "node": "43",
    "class": "WanVideoVAELoader",
    "parameter": "precision",
    "value": "fp16"
  },
  {
    "node": "50",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/Wan2.2-Animate-14B-fp8_v2.safetensors"
  },
  {
    "node": "50",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "sageattn"
  }
]
```

本轮输入覆盖：

```json
{
  "91:text": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "89:value": 864,
  "90:value": 480,
  "100:value": 120,
  "38:seed": 72
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/29-6de9ead9_00001-audio.mp4)；1365113 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/29-6de9ead9_00002-audio.mp4)；1641340 字节。需保持本机SSH隧道及服务器在线。

### API-P07-动作迁移-Wan2.2AnimateV4

- 来源：`registered-api-workflow`；类别：动作迁移；结果：成功。
- 实测任务编号：`148c124c-2e98-44c0-ae30-1b7cda9d6044`；开始UTC：`2026-11-14T19:39:18.053016+00:00`；结束UTC：`2026-11-14T19:42:44.330637+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 22 | WanVideoModelLoader | model | Wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors |
| 38 | WanVideoVAELoader | model_name | wan_2.1_vae.safetensors |
| 65 | WanVideoTextEncodeCached | model_name | umt5-xxl-enc-fp8_e4m3fn.safetensors |
| 71 | CLIPVisionLoader | clip_name | clip_vision_h.safetensors |
| 171 | WanVideoLoraSelectMulti | lora_0 | Wan/WanAnimate_relight_lora_fp16.safetensors |
| 171 | WanVideoLoraSelectMulti | lora_1 | Wan/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors |
| 171 | WanVideoLoraSelectMulti | lora_2 | Wan/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors |
| 171 | WanVideoLoraSelectMulti | lora_3 | Wan/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors |
| 171 | WanVideoLoraSelectMulti | lora_4 | Wan/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors |
| 509 | OnnxDetectionModelLoader | vitpose_model | vitpose-l-wholebody.onnx |
| 509 | OnnxDetectionModelLoader | yolo_model | yolov10m.onnx |

采样与运行参数：

```json
[
  {
    "node": "22",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"
  },
  {
    "node": "22",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "sageattn"
  },
  {
    "node": "27",
    "class": "WanVideoSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "27",
    "class": "WanVideoSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "27",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 5
  },
  {
    "node": "27",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "dpm++_sde"
  },
  {
    "node": "38",
    "class": "WanVideoVAELoader",
    "parameter": "model_name",
    "value": "wan_2.1_vae.safetensors"
  },
  {
    "node": "38",
    "class": "WanVideoVAELoader",
    "parameter": "precision",
    "value": "fp16"
  },
  {
    "node": "51",
    "class": "WanVideoBlockSwap",
    "parameter": "blocks_to_swap",
    "value": 14
  },
  {
    "node": "64",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "65",
    "class": "WanVideoTextEncodeCached",
    "parameter": "model_name",
    "value": "umt5-xxl-enc-fp8_e4m3fn.safetensors"
  },
  {
    "node": "65",
    "class": "WanVideoTextEncodeCached",
    "parameter": "precision",
    "value": "fp32"
  },
  {
    "node": "65",
    "class": "WanVideoTextEncodeCached",
    "parameter": "device",
    "value": "gpu"
  }
]
```

本轮输入覆盖：

```json
{
  "1001:value": 480,
  "1002:value": 864,
  "1003:value": 120,
  "975:seed": 71
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/30-2960bf15_00001-audio.mp4)；3062963 字节。需保持本机SSH隧道及服务器在线。

### API-P17-动作迁移4090-48G显卡专用V8

- 来源：`registered-api-workflow`；类别：动作迁移；结果：执行失败。
- 实测任务编号：`12e19946-6096-40a9-83d5-4123634cc07e`；开始UTC：`2026-11-14T19:42:44.336208+00:00`；结束UTC：`2026-11-14T19:45:14.232488+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 178 | CLIPVisionLoader | clip_name | clip_vision_h.safetensors |
| 204 | OnnxDetectionModelLoader | vitpose_model | vitpose-l-wholebody.onnx |
| 204 | OnnxDetectionModelLoader | yolo_model | yolov10m.onnx |
| 248 | WanVideoLoraSelectMulti | lora_0 | animate/Q弹3.safetensors |
| 276 | WanVideoLoraSelectMulti | lora_0 | Wan/WanAnimate_relight_lora_fp16.safetensors |
| 276 | WanVideoLoraSelectMulti | lora_1 | Wan/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors |
| 276 | WanVideoLoraSelectMulti | lora_2 | Wan/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors |
| 276 | WanVideoLoraSelectMulti | lora_3 | Wan/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors |
| 276 | WanVideoLoraSelectMulti | lora_4 | Wan/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors |
| 277 | WanVideoVAELoader | model_name | Wan2_1_VAE_fp32.safetensors |
| 278 | WanVideoTextEncodeCached | model_name | umt5-xxl-enc-fp8_e4m3fn.safetensors |
| 287 | WanVideoModelLoader | model | Wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors |
| 323 | CheckpointLoaderSimple | ckpt_name | sdpose_wholebody_fp16.safetensors |
| 327 | YOLOModelLoader | model_name | yolo11x-pose.pt |
| 345 | WanVideoUni3C_ControlnetLoader | model | Wan21_Uni3C_controlnet_fp16.safetensors |
| 387 | YOLOModelLoader | model_name | person_detect_v0_l_yv11.pt |

采样与运行参数：

```json
[
  {
    "node": "222",
    "class": "WanVideoSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "222",
    "class": "WanVideoSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "222",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 5
  },
  {
    "node": "222",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "dpm++_sde"
  },
  {
    "node": "225",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "277",
    "class": "WanVideoVAELoader",
    "parameter": "model_name",
    "value": "Wan2_1_VAE_fp32.safetensors"
  },
  {
    "node": "277",
    "class": "WanVideoVAELoader",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "278",
    "class": "WanVideoTextEncodeCached",
    "parameter": "model_name",
    "value": "umt5-xxl-enc-fp8_e4m3fn.safetensors"
  },
  {
    "node": "278",
    "class": "WanVideoTextEncodeCached",
    "parameter": "precision",
    "value": "bf16"
  },
  {
    "node": "278",
    "class": "WanVideoTextEncodeCached",
    "parameter": "device",
    "value": "gpu"
  },
  {
    "node": "287",
    "class": "WanVideoModelLoader",
    "parameter": "model",
    "value": "Wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"
  },
  {
    "node": "287",
    "class": "WanVideoModelLoader",
    "parameter": "attention_mode",
    "value": "sageattn"
  },
  {
    "node": "288",
    "class": "WanVideoBlockSwap",
    "parameter": "blocks_to_swap",
    "value": 8
  },
  {
    "node": "326",
    "class": "SDPoseKeypointExtractor",
    "parameter": "batch_size",
    "value": 16
  },
  {
    "node": "327",
    "class": "YOLOModelLoader",
    "parameter": "model_name",
    "value": "yolo11x-pose.pt"
  },
  {
    "node": "345",
    "class": "WanVideoUni3C_ControlnetLoader",
    "parameter": "model",
    "value": "Wan21_Uni3C_controlnet_fp16.safetensors"
  },
  {
    "node": "345",
    "class": "WanVideoUni3C_ControlnetLoader",
    "parameter": "attention_mode",
    "value": "sageattn"
  },
  {
    "node": "367",
    "class": "WanVideoSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "367",
    "class": "WanVideoSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "367",
    "class": "WanVideoSampler",
    "parameter": "shift",
    "value": 5
  },
  {
    "node": "367",
    "class": "WanVideoSampler",
    "parameter": "scheduler",
    "value": "dpm++_sde"
  },
  {
    "node": "380",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "383",
    "class": "SDPoseKeypointExtractor",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "384",
    "class": "SDPoseKeypointExtractor",
    "parameter": "batch_size",
    "value": 16
  },
  {
    "node": "387",
    "class": "YOLOModelLoader",
    "parameter": "model_name",
    "value": "person_detect_v0_l_yv11.pt"
  }
]
```

本轮输入覆盖：

```json
{
  "300:value": 120,
  "316:value": 480,
  "317:value": 864,
  "222:seed": 70,
  "367:seed": 70
}
```

实测错误（节选；失败不等于成功出片）：

```json
[
  {
    "prompt_id": "12e19946-6096-40a9-83d5-4123634cc07e",
    "node_id": "222",
    "node_type": "WanVideoSampler",
    "executed": [
      "264",
      "400",
      "407",
      "300",
      "410",
      "408",
      "178",
      "274",
      "415",
      "289",
      "370",
      "417",
      "256",
      "276",
      "319",
      "288",
      "409",
      "316",
      "295",
      "433",
      "259",
      "354",
      "318",
      "212",
      "225",
      "275",
      "416",
      "277",
      "317",
      "210"
    ],
    "exception_message": "Allocation on device 0 would exceed allowed memory. (out of memory)\nCurrently allocated     : 28.69 GiB\nRequested               : 1.14 GiB\nDevice limit            : 31.36 GiB\nFree (according to CUDA): 1.69 MiB\nPyTorch limit (set by user-supplied memory fraction)\n                        : 31.36 GiB\nThis error means you ran out of memory on your GPU.\n\nTIPS: If the workflow worked before you might have accidentally set the batch_size to a large number.",
    "exception_type": "torch.OutOfMemoryError",
    "traceback": [
      "  File \"/root/ComfyUI/execution.py\", line 556, in execute\n    output_data, output_ui, has_subgraph, has_pending_tasks = await get_output_data(prompt_id, unique_id, obj, input_data_all, execution_block_cb=execution_block_cb, pre_execute_cb=pre_execute_cb, v3_data=v3_data)\n                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/execution.py\", line 353, in get_output_data\n    return_values = await _async_map_node_over_list(prompt_id, unique_id, obj, input_data_all, obj.FUNCTION, allow_interrupt=True, execution_block_cb=execution_block_cb, pre_execute_cb=pre_execute_cb, v3_data=v3_data)\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/execution.py\", line 327, in _async_map_node_over_list\n    await process_inputs(input_dict, i)\n",
      "  File \"/root/ComfyUI/execution.py\", line 315, in process_inputs\n    result = f(**inputs)\n             ^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/nodes_sampler.py\", line 2498, in process\n    noise_pred, noise_pred_ovi, self.cache_state = predict_with_cfg(\n                                                   ^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/nodes_sampler.py\", line 1671, in predict_with_cfg\n    raise e\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/nodes_sampler.py\", line 1518, in predict_with_cfg\n    noise_pred_cond, noise_pred_ovi, cache_state_cond = transformer(\n                                                        ^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1778, in _wrapped_call_impl\n    return self._call_impl(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1789, in _call_impl\n    return forward_call(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/model.py\", line 3274, in forward\n    x, x_ip, lynx_ref_feature, x_ovi = block(x, x_ip=x_ip, lynx_ref_feature=lynx_ref_feature, x_ovi=x_ovi, x_onetoall_ref=x_onetoall_ref, onetoall_freqs=onetoall_freqs, attention_mode_override=attention_mode, **kwargs)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1778, in _wrapped_call_impl\n    return self._call_impl(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/nn/modules/module.py\", line 1789, in _call_impl\n    return forward_call(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/model.py\", line 1264, in forward\n    y = self.self_attn.forward(q, k, v, seq_lens, lynx_ref_feature=lynx_ref_feature, lynx_ref_scale=lynx_ref_scale,\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/model.py\", line 485, in forward\n    x = attention(q, k, v, k_lens=seq_lens, attention_mode=attention_mode, heads=self.num_heads, frame_tokens=frame_tokens, transformer_options=transformer_options)\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/attention.py\", line 109, in attention\n    return sageattn_func(q, k, v, tensor_layout=\"NHD\").contiguous()\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/_ops.py\", line 1275, in __call__\n    return self._op(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/_library/custom_ops.py\", line 375, in backend_impl\n    result = self._backend_fns[device_type](*args, **kwargs)\n             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/_compile.py\", line 54, in inner\n    return disable_fn(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/_dynamo/eval_frame.py\", line 1298, in _fn\n    return fn(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/torch/_library/custom_ops.py\", line 410, in wrapped_fn\n    return fn(*args, **kwargs)\n           ^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/attention.py\", line 24, in sageattn_func\n    return sageattn(q, k, v, attn_mask=attn_mask, dropout_p=dropout_p, is_causal=is_causal, tensor_layout=tensor_layout)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/python3.12/site-packages/sageattention/core.py\", line 153, in sageattn\n    return sageattn_qk_int8_pv_fp8_cuda(q, k, v, tensor_layout=tensor_layout, is_causal=is_causal, qk_quant_gran=\"per_warp\", sm_scale=sm_scale, return_lse=return_lse, pv_accum_dtype=\"fp32+fp16\") # sm120 has accurate fp32 accumulator for fp8 mma and triton kernel is currently not usable on sm120.\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n",
      "  File \"/root/miniconda3/lib/pyth
```

### API-A01-文生图-Qwen2512高清放大

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`fbd2d612-6246-4f3a-bb5b-3bbb40928712`；开始UTC：`2026-11-14T19:45:14.240605+00:00`；结束UTC：`2026-11-14T19:47:20.828930+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 38 | CLIPLoader | clip_name | qwen_2.5_vl_7b_fp8_scaled.safetensors |
| 39 | VAELoader | vae_name | qwen_image_vae.safetensors |
| 165 | UNETLoader | unet_name | qwen/qwen_image_2512_fp8_e4m3fn.safetensors |
| 287 | LoraLoaderModelOnly | lora_name | Qwen/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors |
| 502 | LoraLoaderModelOnly | lora_name | Qwen/Kook_Qwen_V3极致真实.safetensors |
| 503 | LoraLoaderModelOnly | lora_name | Qwen/Kook_Qwen_真实幻想V2.safetensors |
| 507 | SeedVR2LoadVAEModel | model | ema_vae_fp16.safetensors |
| 511 | SeedVR2LoadDiTModel | model | seedvr2_ema_3b_fp16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "3",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "3",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "3",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "res_2s"
  },
  {
    "node": "3",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "beta57"
  },
  {
    "node": "3",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "38",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "118",
    "class": "CR SDXL Aspect Ratio",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "165",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "507",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "model",
    "value": "ema_vae_fp16.safetensors"
  },
  {
    "node": "507",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "508",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "batch_size",
    "value": 5
  },
  {
    "node": "511",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "model",
    "value": "seedvr2_ema_3b_fp16.safetensors"
  },
  {
    "node": "511",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "511",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "blocks_to_swap",
    "value": 32
  },
  {
    "node": "511",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "attention_mode",
    "value": "sdpa"
  }
]
```

本轮输入覆盖：

```json
{
  "187:text": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "515:value": 864,
  "516:value": 480,
  "3:seed": 91,
  "508:seed": 91
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/32-8040e06c_00001_.png)；9216660 字节。需保持本机SSH隧道及服务器在线。

### API-A08-洗图-Qwen二次元转真人高清放大

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`18a53279-9b86-4a07-867d-ca3e0b64bd6c`；开始UTC：`2026-11-14T19:47:20.834729+00:00`；结束UTC：`2026-11-14T19:51:30.824447+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 38 | CLIPLoader | clip_name | qwen_2.5_vl_7b_fp8_scaled.safetensors |
| 39 | VAELoader | vae_name | qwen_image_vae.safetensors |
| 431 | LoraLoaderModelOnly | lora_name | Qwen/AnythingtoRealCharacters2511_20.safetensors |
| 439 | LoraLoaderModelOnly | lora_name | Qwen/BJD娃娃V2.0_04.safetensors |
| 444 | LoraLoaderModelOnly | lora_name | Qwen/Qwen动漫转写实真人V2_V2.safetensors |
| 446 | LoraLoaderModelOnly | lora_name | Qwen/Qwen-Image-Edit-2511-Lightning-8steps-V1.0-bf16.safetensors |
| 472 | SeedVR2LoadVAEModel | model | ema_vae_fp16.safetensors |
| 474 | SeedVR2LoadDiTModel | model | seedvr2_ema_3b-Q4_K_M.gguf |
| 480 | UNETLoader | unet_name | Zimage/z_image_turbo_int8_convrot.safetensors |
| 489 | CLIPLoader | clip_name | qwen_3_4b_int8_convrot.safetensors |
| 493 | VAELoader | vae_name | flux_ultra_vae.safetensors |
| 526 | ControlNetLoader | control_net_name | Qwen-Image-ControlNet-Union.safetensors |
| 554 | UNETLoader | unet_name | qwen/qwen_image_edit_2511_int8_convrot.safetensors |
| 565 | llama_cpp_model_loader | model | Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf |
| 565 | llama_cpp_model_loader | mmproj | mmproj-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf |

采样与运行参数：

```json
[
  {
    "node": "38",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "347",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "347",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "347",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "347",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "347",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 0.8000000000000002
  },
  {
    "node": "472",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "model",
    "value": "ema_vae_fp16.safetensors"
  },
  {
    "node": "472",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "474",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "model",
    "value": "seedvr2_ema_3b-Q4_K_M.gguf"
  },
  {
    "node": "474",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "474",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "blocks_to_swap",
    "value": 32
  },
  {
    "node": "474",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "attention_mode",
    "value": "sdpa"
  },
  {
    "node": "480",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "482",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "batch_size",
    "value": 5
  },
  {
    "node": "484",
    "class": "KSampler",
    "parameter": "steps",
    "value": 5
  },
  {
    "node": "484",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "484",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "dpmpp_2m_sde"
  },
  {
    "node": "484",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "FlowMatchEulerDiscreteScheduler"
  },
  {
    "node": "484",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 0.010000000000000002
  },
  {
    "node": "487",
    "class": "KSampler",
    "parameter": "steps",
    "value": 10
  },
  {
    "node": "487",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1.6
  },
  {
    "node": "487",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "487",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "487",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 0.30000000000000004
  },
  {
    "node": "489",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "554",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "565",
    "class": "llama_cpp_model_loader",
    "parameter": "model",
    "value": "Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf"
  }
]
```

本轮输入覆盖：

```json
{
  "347:seed": 90,
  "482:seed": 90,
  "484:seed": 90,
  "487:seed": 90,
  "563:seed": 90
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/33-05f62a50_00001_.png)；10297618 字节。需保持本机SSH隧道及服务器在线。

### API-B13-千问角色一键多角度_multiple_character_angles-v1.0

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`1a3ef7ee-5831-4fb5-b4d0-e44db7ff995f`；开始UTC：`2026-11-14T19:51:30.831613+00:00`；结束UTC：`2026-11-14T19:53:20.247820+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 48:9 | VAELoader | vae_name | qwen_image_vae.safetensors |
| 48:10 | CLIPLoader | clip_name | qwen_2.5_vl_7b_fp8_scaled.safetensors |
| 48:12 | UNETLoader | unet_name | qwen/qwen_image_edit_2509_fp8_e4m3fn.safetensors |
| 48:20 | LoraLoaderModelOnly | lora_name | Qwen/Qwen-Edit-2509-Multiple-angles.safetensors |
| 48:26 | LoraLoaderModelOnly | lora_name | Qwen/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "48:10",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "48:12",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "65:35:77",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:35:81",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:35:81",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:35:81",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:35:81",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:35:81",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:37:86",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:37:90",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:37:90",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:37:90",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:37:90",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:37:90",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:39:95",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:39:99",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:39:99",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:39:99",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:39:99",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:39:99",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:42:113",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:42:117",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:42:117",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:42:117",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:42:117",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:42:117",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:44:122",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:44:126",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:44:126",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:44:126",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:44:126",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:44:126",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:46:131",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:46:138",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:46:138",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:46:138",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:46:138",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:46:138",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:40:104",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:40:108",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:40:108",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:40:108",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:40:108",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:40:108",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "65:33:11",
    "class": "ModelSamplingAuraFlow",
    "parameter": "shift",
    "value": 3
  },
  {
    "node": "65:33:21",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "65:33:21",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "65:33:21",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "65:33:21",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "65:33:21",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "65:35:81:seed": 89,
  "65:37:90:seed": 89,
  "65:39:99:seed": 89,
  "65:42:117:seed": 89,
  "65:44:126:seed": 89,
  "65:46:138:seed": 89,
  "65:40:108:seed": 89,
  "65:33:21:seed": 89
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00001_.png)；926814 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00002_.png)；918851 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00003_.png)；849294 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00004_.png)；889556 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00005_.png)；852560 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00006_.png)；1005039 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00007_.png)；897843 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/34-208941dc_00008_.png)；820888 字节。需保持本机SSH隧道及服务器在线。

### API-B18-Qwenimage2.1

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`f6d61243-5d80-4158-a39b-c6ff6fec023b`；开始UTC：`2026-11-14T19:53:20.253846+00:00`；结束UTC：`2026-11-14T19:54:09.409145+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 4 | CLIPLoader | clip_name | qwen3vl_8b_int8_convrot.safetensors |
| 5 | UNETLoader | unet_name | qwen/qwen_image_2.1_int8_convrot.safetensors |
| 13 | VAELoader | vae_name | qwen_image_2.1_vae_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "4",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "5",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "23",
    "class": "KSampler",
    "parameter": "steps",
    "value": 20
  },
  {
    "node": "23",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "23",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "23",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "23",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "36",
    "class": "EmptyLatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "39",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "40",
    "class": "QwenImage21Cache",
    "parameter": "device",
    "value": "auto"
  },
  {
    "node": "40",
    "class": "QwenImage21Cache",
    "parameter": "dtype",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "37:prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "37:negative_prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "42:megapixels": 0.4,
  "23:seed": 53
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/35-bc788833_00001.png)；516720 字节。需保持本机SSH隧道及服务器在线。

### API-B20-Qwen-Image-2.1-Turbo高速编辑版

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`a3105dac-3f81-45ad-b438-23bd22b48379`；开始UTC：`2026-11-14T19:54:09.414909+00:00`；结束UTC：`2026-11-14T19:55:30.988624+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 22:3 | VAELoader | vae_name | qwen_image_2.1_vae_bf16.safetensors |
| 22:2 | CLIPLoader | clip_name | qwen3vl_8b_bf16.safetensors |
| 22:1 | UNETLoader | unet_name | qwen/qwen_image_2.1_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "5",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "7",
    "class": "SamplerCustom",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "22:2",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "22:1",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "4:prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "4:negative_prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "7:noise_seed": 88
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/36-29f200c4_00001_.png)；1263830 字节。需保持本机SSH隧道及服务器在线。

### API-C16-短剧文生图专用-支持场景-角色

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`a7fd3819-2286-4328-b1f9-067823aa586f`；开始UTC：`2026-11-14T19:55:30.994003+00:00`；结束UTC：`2026-11-14T19:56:52.802954+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 11 | VAELoader | vae_name | ae.safetensors |
| 12 | CLIPLoader | clip_name | qwen_3_4b.safetensors |
| 14 | LoraLoaderModelOnly | lora_name | Zimage/Z-Image-Fun-Lora-Distill-8-Steps-2603-ComfyUI.safetensors |
| 18 | UNETLoader | unet_name | Zimage/z_image_bf16.safetensors |
| 23 | LoraLoaderModelOnly | lora_name | Zimage/Kook_Zimage_瑶光.safetensors |
| 33 | LoraLoaderModelOnly | lora_name | Zimage/Kook_Zimage_如梦似幻.safetensors |
| 53 | SeedVR2LoadDiTModel | model | seedvr2_ema_3b_fp8_e4m3fn.safetensors |
| 54 | SeedVR2LoadVAEModel | model | ema_vae_fp16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "12",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "18",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "21",
    "class": "EmptyLatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "22",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "22",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "22",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "res_2s_ode"
  },
  {
    "node": "22",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "kl_optimal"
  },
  {
    "node": "22",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "53",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "model",
    "value": "seedvr2_ema_3b_fp8_e4m3fn.safetensors"
  },
  {
    "node": "53",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "53",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "blocks_to_swap",
    "value": 32
  },
  {
    "node": "53",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "attention_mode",
    "value": "sageattn_2"
  },
  {
    "node": "54",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "model",
    "value": "ema_vae_fp16.safetensors"
  },
  {
    "node": "54",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "72",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "batch_size",
    "value": 5
  }
]
```

本轮输入覆盖：

```json
{
  "49:text": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "60:value": 864,
  "61:value": 480,
  "22:seed": 87,
  "72:seed": 87
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/37-c57791db_00001_.png)；2359390 字节。需保持本机SSH隧道及服务器在线。

### API-C18-豹豹喵呜制作-白玉AIO三采超高清写真生成

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`83a8d79f-c46a-4c72-a467-8ccbc8a60e36`；开始UTC：`2026-11-14T19:56:52.808662+00:00`；结束UTC：`2026-11-14T19:59:22.526840+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 27 | CheckpointLoaderSimple | ckpt_name | Zimage/Z-Image-Base-8steps-White_Marble-AIO_v2-bf16.safetensors |
| 33 | UNETLoader | unet_name | flux/Flux2-Klein-9B-True-v2-fp8mixed.safetensors |
| 34 | CLIPLoader | clip_name | qwen_3_8b_fp8mixed.safetensors |
| 35 | VAELoader | vae_name | flux2-vae.safetensors |
| 40 | Lora Loader Stack (rgthree) | lora_01 | Flux/klein_9B_Turbo_r128.safetensors |
| 40 | Lora Loader Stack (rgthree) | lora_02 | Flux/f2k_9B_小志一致性(0.5-0.7)lcs_consist_0412预览版preview.safetensors |
| 50 | UNETLoader | unet_name | Zimage/z_image_turbo_bf16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "28",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "28",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "28",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "res_2s"
  },
  {
    "node": "28",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "linear_quadratic"
  },
  {
    "node": "28",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "33",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "34",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "45",
    "class": "KSampler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "45",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "45",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "45",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "45",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "49",
    "class": "KSamplerAdvanced",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "49",
    "class": "KSamplerAdvanced",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "49",
    "class": "KSamplerAdvanced",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "49",
    "class": "KSamplerAdvanced",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "50",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "77:text": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "113:自定义宽": 864,
  "113:自定义高": 480,
  "81:seed": 86
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/38-444552a2_00001_.png)；1995343 字节。需保持本机SSH隧道及服务器在线。

### API-C19-人物设定三视图zimage双采

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`72fc8d89-cc26-4500-b68b-0424afc346a4`；开始UTC：`2026-11-14T19:59:22.533322+00:00`；结束UTC：`2026-11-14T20:01:24.539592+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 39 | llama_cpp_model_loader | model | Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf |
| 39 | llama_cpp_model_loader | mmproj | mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf |
| 48 | CheckpointLoaderSimple | ckpt_name | Zimage/Z-Image-Base-8steps-White_Marble-AIO_v2-bf16.safetensors |
| 58 | UNETLoader | unet_name | Zimage/z_image_turbo_bf16.safetensors |
| 67 | SeedVR2LoadDiTModel | model | seedvr2_ema_3b-Q4_K_M.gguf |
| 68 | SeedVR2LoadVAEModel | model | ema_vae_fp16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "39",
    "class": "llama_cpp_model_loader",
    "parameter": "model",
    "value": "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf"
  },
  {
    "node": "47",
    "class": "EmptyLatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "49",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "49",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "49",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "res_2s"
  },
  {
    "node": "49",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "linear_quadratic"
  },
  {
    "node": "49",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "57",
    "class": "KSamplerAdvanced",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "58",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "67",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "model",
    "value": "seedvr2_ema_3b-Q4_K_M.gguf"
  },
  {
    "node": "67",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "67",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "blocks_to_swap",
    "value": 32
  },
  {
    "node": "67",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "attention_mode",
    "value": "sageattn_2"
  },
  {
    "node": "68",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "model",
    "value": "ema_vae_fp16.safetensors"
  },
  {
    "node": "68",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "69",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "batch_size",
    "value": 5
  }
]
```

本轮输入覆盖：

```json
{
  "42:prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "47:width": 864,
  "47:height": 480,
  "38:seed": 85,
  "49:seed": 85,
  "57:noise_seed": 85,
  "69:seed": 85
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/39-ee10ca18_00001_.png)；9708272 字节。需保持本机SSH隧道及服务器在线。

### API-D14-分镜-Flux克莱因9B多角度多场景

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`490f4261-b637-4d58-ad74-6c3c90972353`；开始UTC：`2026-11-14T20:01:24.547251+00:00`；结束UTC：`2026-11-14T20:03:02.382402+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 232 | VAELoader | vae_name | flux2-vae.safetensors |
| 236 | CLIPLoader | clip_name | qwen_3_8b_fp8mixed.safetensors |
| 239 | UNETLoader | unet_name | flux/flux-2-klein-9b-fp8.safetensors |
| 263 | llama_cpp_model_loader | model | Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf |
| 263 | llama_cpp_model_loader | mmproj | mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf |

采样与运行参数：

```json
[
  {
    "node": "221",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "223",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "226",
    "class": "Flux2Scheduler",
    "parameter": "steps",
    "value": 4
  },
  {
    "node": "236",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "239",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "251",
    "class": "EmptyFlux2LatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "263",
    "class": "llama_cpp_model_loader",
    "parameter": "model",
    "value": "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf"
  }
]
```

本轮输入覆盖：

```json
{
  "222:noise_seed": 84,
  "262:seed": 84
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00001_.png)；1744977 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00002_.png)；2117784 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00003_.png)；2079294 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00004_.png)；1656992 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00005_.png)；1951211 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00006_.png)；1944283 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00007_.png)；1971340 字节。需保持本机SSH隧道及服务器在线。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/40-0ee6e189_00008_.png)；1608186 字节。需保持本机SSH隧道及服务器在线。

### API-D18-klein9b真人剧制造机-多图编辑

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`c96ca3f1-8d2f-4529-95fd-d3994cb5d6b2`；开始UTC：`2026-11-14T20:03:02.387609+00:00`；结束UTC：`2026-11-14T20:05:11.902766+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 1057 | llama_cpp_model_loader | model | Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf |
| 1057 | llama_cpp_model_loader | mmproj | mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf |
| 1238 | SeedVR2LoadDiTModel | model | seedvr2_ema_3b_fp16.safetensors |
| 1239 | SeedVR2LoadVAEModel | model | ema_vae_fp16.safetensors |
| 1102:1101 | VAELoader | vae_name | flux2-vae.safetensors |
| 1102:1100 | CLIPLoader | clip_name | qwen_3_8b_fp8mixed.safetensors |
| 1102:1099 | UNETLoader | unet_name | flux/flux-2-klein-9b.safetensors |

采样与运行参数：

```json
[
  {
    "node": "1057",
    "class": "llama_cpp_model_loader",
    "parameter": "model",
    "value": "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
  },
  {
    "node": "1232",
    "class": "EmptyLatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "1238",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "model",
    "value": "seedvr2_ema_3b_fp16.safetensors"
  },
  {
    "node": "1238",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "1238",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "blocks_to_swap",
    "value": 32
  },
  {
    "node": "1238",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "attention_mode",
    "value": "sdpa"
  },
  {
    "node": "1239",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "model",
    "value": "ema_vae_fp16.safetensors"
  },
  {
    "node": "1239",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "1240",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "batch_size",
    "value": 5
  },
  {
    "node": "1102:1100",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "1102:1099",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "1102:867",
    "class": "KSampler",
    "parameter": "steps",
    "value": 6
  },
  {
    "node": "1102:867",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "1102:867",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "1102:867",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "1102:867",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "1232:width": 864,
  "1232:height": 480,
  "1058:seed": 83,
  "1240:seed": 83,
  "1102:867:seed": 83
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/41-6be12d4f_00001_.png)；11070733 字节。需保持本机SSH隧道及服务器在线。

### API-D20-RAW画质重建Adonis_Workflow

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`8484b317-78ce-4d00-987d-ceb1a8c1578f`；开始UTC：`2026-11-14T20:05:11.934455+00:00`；结束UTC：`2026-11-14T20:06:27.737118+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 366 | UNETLoader | unet_name | flux/flux-2-klein-9b-fp8.safetensors |
| 382 | LoraLoaderModelOnly | lora_name | Flux/flux2klein_adonis_refine.safetensors |
| 383 | LoraLoaderModelOnly | lora_name | Flux/flux2klein_adonis_base.safetensors |
| 384 | VAELoader | vae_name | flux2-vae.safetensors |
| 386 | CLIPLoader | clip_name | qwen_3_8b_fp8mixed.safetensors |

采样与运行参数：

```json
[
  {
    "node": "312",
    "class": "FastFilmGrain",
    "parameter": "batch_size",
    "value": 3
  },
  {
    "node": "366",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "371",
    "class": "EmptyFlux2LatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "380",
    "class": "ClownsharKSampler_Beta",
    "parameter": "sampler_name",
    "value": "exponential/res_2s"
  },
  {
    "node": "380",
    "class": "ClownsharKSampler_Beta",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "380",
    "class": "ClownsharKSampler_Beta",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "380",
    "class": "ClownsharKSampler_Beta",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "381",
    "class": "ClownsharKSampler_Beta",
    "parameter": "sampler_name",
    "value": "exponential/res_2s"
  },
  {
    "node": "381",
    "class": "ClownsharKSampler_Beta",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "381",
    "class": "ClownsharKSampler_Beta",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "381",
    "class": "ClownsharKSampler_Beta",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "386",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "387:seed": 82
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/42-ca6b9078_00001_.png)；3115238 字节。需保持本机SSH隧道及服务器在线。

### API-T10-Krea2做剧图像4视图

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`e0ca9364-a9be-420d-9a25-6afae3d8b558`；开始UTC：`2026-11-14T20:06:27.742951+00:00`；结束UTC：`2026-11-14T20:07:38.487667+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 122 | CLIPLoader | clip_name | qwen3vl_4b_fp8_scaled.safetensors |
| 123 | VAELoader | vae_name | qwen_image_vae.safetensors |
| 128 | UNETLoader | unet_name | krea/krea2_turbo_int8_convrot.safetensors |
| 145 | LoraLoaderModelOnly | lora_name | krea2/krea2_4panel.safetensors |

采样与运行参数：

```json
[
  {
    "node": "122",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "128",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "136",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "141",
    "class": "EmptySD3LatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "142",
    "class": "KSampler",
    "parameter": "steps",
    "value": 10
  },
  {
    "node": "142",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "142",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "142",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "142",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "141:width": 864,
  "141:height": 480,
  "142:seed": 69
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/43-55c4c824_00001_.png)；458576 字节。需保持本机SSH隧道及服务器在线。

### API-T15-MJ风格文生图

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`0f69fbce-b1a7-48f8-a3d8-147152f457ac`；开始UTC：`2026-11-14T20:07:38.493193+00:00`；结束UTC：`2026-11-14T20:08:24.623506+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 171 | LoraLoaderModelOnly | lora_name | krea2/cinematic_movie_still_krea2.safetensors |
| 172 | CLIPLoader | clip_name | qwen3vl_4b_fp8_scaled.safetensors |
| 181 | UNETLoader | unet_name | krea/krea2_turbo_int8_convrot.safetensors |
| 182 | VAELoader | vae_name | qwen_image_vae.safetensors |
| 183 | LoraLoaderModelOnly | lora_name | krea2/alternative_reality_v1p.safetensors |
| 188 | LoraLoaderModelOnly | lora_name | krea2/krea2-Cc-MJ-影视柔光.safetensors |
| 189 | LoraLoaderModelOnly | lora_name | krea2/krea2-Cc-MJ-风格滤镜.safetensors |
| 190 | LoraLoaderModelOnly | lora_name | krea2/babegenerator.ink-realism_helper.safetensors |
| 194 | LoraLoaderModelOnly | lora_name | krea2/detail_slider_krea2_loraholic.safetensors |

采样与运行参数：

```json
[
  {
    "node": "172",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "174",
    "class": "EmptyLatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "181",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "186",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "186",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "186",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "186",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "186",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "187:prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "193:megapixels": 0.4,
  "186:seed": 45
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/44-586890a7_00001_.png)；580028 字节。需保持本机SSH隧道及服务器在线。

### API-T4-Krea2-int8-角色设定三视图

- 来源：`registered-api-workflow`；类别：图像；结果：成功。
- 实测任务编号：`9f0dd8c9-b950-43ae-b441-9b8c4f64cdeb`；开始UTC：`2026-11-14T20:08:24.629001+00:00`；结束UTC：`2026-11-14T20:09:57.331303+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 55 | UNETLoader | unet_name | krea/redcraft2KREA2INT8_11INT8Native.safetensors |
| 56 | CLIPLoader | clip_name | qwen3vl_4b_uncensored_int8_convrot.safetensors |
| 57 | VAELoader | vae_name | qwen_image_vae.safetensors |
| 110 | llama_cpp_model_loader | model | Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf |
| 110 | llama_cpp_model_loader | mmproj | mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf |
| 129 | LoraLoaderModelOnly | lora_name | krea2/krea2-Cc风情万种-人像.safetensors |

采样与运行参数：

```json
[
  {
    "node": "52",
    "class": "EmptyLatentImage",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "53",
    "class": "KSampler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "53",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "53",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "53",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "53",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "55",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "56",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "110",
    "class": "llama_cpp_model_loader",
    "parameter": "model",
    "value": "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf"
  }
]
```

本轮输入覆盖：

```json
{
  "52:width": 864,
  "52:height": 480,
  "121:prompt": "A photorealistic cinematic portrait of an adult woman in a blue jacket, soft daylight, clean background, no text, no watermark.",
  "109:seed": 68,
  "115:seed": 68
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/45-482e916a_00001_.png)；559850 字节。需保持本机SSH隧道及服务器在线。

### API-U00-minimax_h3提示词QWEN3.8群主版

- 来源：`registered-api-workflow`；类别：提示词；结果：成功。
- 为隔离复测而重启服务耗时45.179秒，单列且不包含在请求墙钟耗时中；已计入整体开机窗口。
- 实测任务编号：`6a06b686-cb74-4401-812e-bd2f355fb47d`；开始UTC：`2026-11-15T05:14:54.282974+00:00`；结束UTC：`2026-11-15T05:16:25.612668+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 14 | ZealmanLLM_ModelLoader | 主模型 | Qwen3.8-27B-Q4_K_M.gguf |
| 14 | ZealmanLLM_ModelLoader | 视觉投影mmproj | Qwen3.8-mmproj-BF16.gguf |

采样与运行参数：

```json
[]
```

本轮输入覆盖：

```json
{
  "15:提示词": "请根据图1编写一个五秒镜头的简短中文视频提示词，人物微笑并轻轻转头。",
  "15:seed": 67
}
```

- 共2次尝试，所有尝试等效费用合计0.0589元。下列主结果采用最后一次记录；历史失败与实际输入见JSON的attempts字段。

### API-M19去字幕

- 来源：`registered-api-workflow`；类别：视频后期；结果：成功。
- 实测任务编号：`20194520-4a4a-45d6-a378-4dbe8f8dc3b0`；开始UTC：`2026-11-15T04:44:50.655002+00:00`；结束UTC：`2026-11-15T04:46:48.987076+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 457 | LoraLoaderModelOnly | lora_name | Ltx/ltx2.3-ic-watermark-remove-general.safetensors |
| 468 | LoraLoaderModelOnly | lora_name | Ltx/ltx2.3-ic-subtitles-remove-general.safetensors |
| 512 | UNETLoader | unet_name | Ltx/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors |
| 513 | VAELoader | vae_name | ltx-2.5-video-vae-bf16.safetensors |
| 515 | CLIPLoader | clip_name | gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors |

采样与运行参数：

```json
[
  {
    "node": "129",
    "class": "CFGGuider",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "137",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler_ancestral_cfg_pp"
  },
  {
    "node": "512",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "515",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  }
]
```

本轮输入覆盖：

```json
{
  "115:noise_seed": 47
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/47-7e7935fe_00001-audio.mp4)；1461477 字节。需保持本机SSH隧道及服务器在线。

### API-M20-RelayVSR视频高速超分2x

- 来源：`registered-api-workflow`；类别：视频后期；结果：成功。
- 实测任务编号：`b47eb908-e1eb-4697-a19f-cdf0ab06389c`；开始UTC：`2026-11-15T04:46:48.992605+00:00`；结束UTC：`2026-11-15T04:47:18.264197+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 4 | UNETLoader | unet_name | RelayVSR/relayvsr_x2_int8_convrot.safetensors |
| 7 | VAELoader | vae_name | relayvsr_flash_vae_x2_fp32.safetensors |

采样与运行参数：

```json
[
  {
    "node": "4",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "6",
    "class": "KSampler",
    "parameter": "steps",
    "value": 1
  },
  {
    "node": "6",
    "class": "KSampler",
    "parameter": "cfg",
    "value": 1
  },
  {
    "node": "6",
    "class": "KSampler",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "6",
    "class": "KSampler",
    "parameter": "scheduler",
    "value": "simple"
  },
  {
    "node": "6",
    "class": "KSampler",
    "parameter": "denoise",
    "value": 1
  }
]
```

本轮输入覆盖：

```json
{
  "6:seed": 43
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/48-76805d15_00001_.mp4)；6716259 字节。需保持本机SSH隧道及服务器在线。

### API-Z10-专业视频补帧

- 来源：`registered-api-workflow`；类别：视频后期；结果：成功。
- 实测任务编号：`5ecc70c7-768d-4e30-ae1b-5a97bf484341`；开始UTC：`2026-11-15T04:47:18.270086+00:00`；结束UTC：`2026-11-15T04:47:49.527166+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 1 | DownloadAndLoadGIMMVFIModel | model | gimmvfi_r_arb_lpips_fp32.safetensors |

采样与运行参数：

```json
[
  {
    "node": "1",
    "class": "DownloadAndLoadGIMMVFIModel",
    "parameter": "model",
    "value": "gimmvfi_r_arb_lpips_fp32.safetensors"
  },
  {
    "node": "1",
    "class": "DownloadAndLoadGIMMVFIModel",
    "parameter": "precision",
    "value": "fp16"
  }
]
```

本轮输入覆盖：

```json
{
  "3:seed": 46
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/49-c67a8024_00001-audio.mp4)；1526577 字节。需保持本机SSH隧道及服务器在线。

### API-N2-单人声音克隆FishAudioS2pro

- 来源：`registered-api-workflow`；类别：语音；结果：成功。
- 实测任务编号：`43e6847e-5a1d-4e9e-8666-a99688ae9c8e`；开始UTC：`2026-11-15T04:47:49.532755+00:00`；结束UTC：`2026-11-15T04:49:20.573333+00:00`。

模板外层未列出权重文件；具体节点与设置见JSON。

采样与运行参数：

```json
[
  {
    "node": "13",
    "class": "Apply Whisper",
    "parameter": "model",
    "value": "large-v3"
  },
  {
    "node": "25",
    "class": "FishS2VoiceCloneTTS",
    "parameter": "model_path",
    "value": "s2-pro"
  },
  {
    "node": "25",
    "class": "FishS2VoiceCloneTTS",
    "parameter": "device",
    "value": "cuda"
  },
  {
    "node": "25",
    "class": "FishS2VoiceCloneTTS",
    "parameter": "precision",
    "value": "bfloat16"
  },
  {
    "node": "25",
    "class": "FishS2VoiceCloneTTS",
    "parameter": "attention",
    "value": "auto"
  }
]
```

本轮输入覆盖：

```json
{
  "25:text": "这是一段用于 LichTV 性能测试的语音。",
  "25:seed": 73
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/50-7203abc3_00001.flac)；127176 字节。需保持本机SSH隧道及服务器在线。

### API-U00-首页H3多参考

- 来源：`API-U00-闹闹版_sK.json`；类别：H3视频；结果：成功。
- 实测任务编号：`77c0c097-483f-4d0f-822f-e78d5ab7a672`；开始UTC：`2026-11-15T04:49:20.580250+00:00`；结束UTC：`2026-11-15T04:53:21.404752+00:00`。
- 含封装节点：部分主模型、编码器或采样配置在外层不可见，不能确认全部内部配置。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 208 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |

采样与运行参数：

```json
[
  {
    "node": "141",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "259",
    "class": "ZealmanH3PickReferenceMedia",
    "parameter": "fps",
    "value": 24
  }
]
```

本轮输入覆盖：

```json
{
  "259:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "259:seconds": 5,
  "259:megapixels": 0.4
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/51-e2f2dff5_00001-audio.mp4)；2003651 字节。需保持本机SSH隧道及服务器在线。

### API-U06-首页视频生成V5

- 来源：`U06-minimax_h3_lightX2v多图参考生视频V5.json`；类别：H3视频；结果：成功。
- 实测任务编号：`3fd95107-63e4-41fb-ac26-fb609f08cf95`；开始UTC：`2026-11-15T05:13:11.201176+00:00`；结束UTC：`2026-11-15T05:14:54.135580+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 119 | VAELoader | vae_name | minimax_h3_video_vae_int8_convrot.safetensors |
| 120 | VAELoader | vae_name | minimax_h3_audio_vae_fp32.safetensors |
| 128 | CLIPLoader | clip_name | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors |
| 620 | UNETLoader | unet_name | minimax/minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| 677 | ModelPreviewOverrideKJ | tiny_vae | taeh3.safetensors |
| 710 | LoraLoaderModelOnly | lora_name | minimax/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors |

采样与运行参数：

```json
[
  {
    "node": "128",
    "class": "CLIPLoader",
    "parameter": "device",
    "value": "default"
  },
  {
    "node": "620",
    "class": "UNETLoader",
    "parameter": "weight_dtype",
    "value": "default"
  },
  {
    "node": "725",
    "class": "KSamplerSelect",
    "parameter": "sampler_name",
    "value": "euler"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "scheduler",
    "value": "beta"
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "steps",
    "value": 8
  },
  {
    "node": "728",
    "class": "BasicScheduler",
    "parameter": "denoise",
    "value": 1
  },
  {
    "node": "732",
    "class": "VHS_VideoCombine",
    "parameter": "frame_rate",
    "value": 24
  },
  {
    "node": "736",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "739",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "742",
    "class": "ImageResizeKJv2",
    "parameter": "device",
    "value": "cpu"
  },
  {
    "node": "748",
    "class": "ModelAttentionBackend",
    "parameter": "attention",
    "value": "comfy kitchen attention"
  },
  {
    "node": "1311",
    "class": "H3SigmaRefiner",
    "parameter": "extra_steps",
    "value": 2
  },
  {
    "node": "1311",
    "class": "H3SigmaRefiner",
    "parameter": "start_at_sigma",
    "value": 0.65
  },
  {
    "node": "1311",
    "class": "H3SigmaRefiner",
    "parameter": "end_at_sigma",
    "value": 0.0
  }
]
```

本轮输入覆盖：

```json
{
  "132:value": 5,
  "664:prompt": "A cinematic five-second shot of the adult woman in <Picture 1>, wearing the same outfit, gently smiling and turning toward the camera. Natural motion, stable identity, soft daylight, no subtitles, no watermark.",
  "142:seed": 92,
  "665:megapixels": 0.4
}
```

- 共2次尝试，所有尝试等效费用合计0.2411元。下列主结果采用最后一次记录；历史失败与实际输入见JSON的attempts字段。

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/02-97cdca3d_00001-audio.mp4)；6497351 字节。需保持本机SSH隧道及服务器在线。

### API-M02-首页画质增强

- 来源：`M02-放大-SeedVR2+TTP高清放大.json`；类别：图像后期；结果：成功。
- 实测任务编号：`fc93d13e-2c2e-40d2-b1dc-0e6e9ec3d2cd`；开始UTC：`2026-11-15T04:56:30.073775+00:00`；结束UTC：`2026-11-15T04:57:22.359162+00:00`。

| 节点 | 加载器 | 配置字段 | 模型文件 |
|---|---|---|---|
| 109 | SeedVR2LoadDiTModel | model | seedvr2_ema_3b_fp8_e4m3fn.safetensors |
| 110 | SeedVR2LoadVAEModel | model | ema_vae_fp16.safetensors |

采样与运行参数：

```json
[
  {
    "node": "108",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "seed",
    "value": 95
  },
  {
    "node": "108",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "batch_size",
    "value": 1
  },
  {
    "node": "108",
    "class": "SeedVR2VideoUpscaler",
    "parameter": "offload_device",
    "value": "cpu"
  },
  {
    "node": "109",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "model",
    "value": "seedvr2_ema_3b_fp8_e4m3fn.safetensors"
  },
  {
    "node": "109",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "109",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "blocks_to_swap",
    "value": 36
  },
  {
    "node": "109",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "offload_device",
    "value": "cpu"
  },
  {
    "node": "109",
    "class": "SeedVR2LoadDiTModel",
    "parameter": "attention_mode",
    "value": "sdpa"
  },
  {
    "node": "110",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "model",
    "value": "ema_vae_fp16.safetensors"
  },
  {
    "node": "110",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "device",
    "value": "cuda:0"
  },
  {
    "node": "110",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "encode_tiled",
    "value": true
  },
  {
    "node": "110",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "decode_tiled",
    "value": true
  },
  {
    "node": "110",
    "class": "SeedVR2LoadVAEModel",
    "parameter": "offload_device",
    "value": "cpu"
  }
]
```

本轮输入覆盖：

```json
{
  "108:seed": 95
}
```

- 产出文件：[查看或下载](http://127.0.0.1:18008/output/lichtv-benchmark-20261115/53-017c7c61_00001_.png)；17718457 字节。需保持本机SSH隧道及服务器在线。

## 原始数据

- [精简汇总CSV表格](../../assets/benchmarks/lichtv-2026-11-15/summary.csv)
- [模型配置CSV表格](../../assets/benchmarks/lichtv-2026-11-15/model-configs.csv)
- [含完整配置字段的CSV](../../assets/benchmarks/lichtv-2026-11-15/results.csv)
- [完整配置与实测JSON](../../assets/benchmarks/lichtv-2026-11-15/results.json)

原始工作流、含封装载荷的请求和完整执行历史保留在GPU服务器受保护目录 `/root/lichtv-benchmark-20261115/`。完整提交计划为 `plans-with-homepage.json`，最终有效输入计划为 `plans-final-valid-inputs.json`，含首次原生高分辨率档的计划另保留。执行脚本快照在 `scripts/`；不公开服务密钥或原始参考素材。JSON中同时列出节点所属模块、组件设置和首轮准备模板SHA256（补测实际参数以test_overrides和attempts为准），封装内部不可见部分仍明确标为未知。
