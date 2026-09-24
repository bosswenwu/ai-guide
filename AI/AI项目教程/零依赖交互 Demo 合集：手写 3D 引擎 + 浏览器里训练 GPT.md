# 零依赖交互 Demo 合集：手写 3D 引擎 + 浏览器里训练 GPT

> 👉 **<a href="/demos/" target="_blank" rel="noopener">点这里打开 Demo 合集页</a>**（建议桌面浏览器，3D Demo 需要 WebGL）

这是四个可以直接玩的网页 Demo，全部**纯手写、零依赖**——没有 Three.js，没有 PyTorch，没有任何 npm 包。每个都是一个自包含的 HTML 文件，右键「查看网页源代码」就能看到全部实现。

做这组 Demo 的初衷是想验证一件事：**在「不许用库」的约束下，浏览器原生能力的天花板到底在哪里。** 结论比预期高得多——一个 3D 探索游戏和一个能真正训练的神经网络，都塞得进单个 HTML 文件里。

| Demo | 一句话 | 核心技术 |
| --- | --- | --- |
| <a href="/demos/train-gpt.html" target="_blank" rel="noopener">🧠 从零训练一个 GPT</a> | 真的在浏览器里训练神经网络 | 手写 Transformer + 反向传播 + Adam |
| <a href="/demos/clocktower.html" target="_blank" rel="noopener">🕰️ The Clocktower Fell Silent</a> | 第一人称低多边形村庄探索 | 手写 WebGL 引擎 |
| <a href="/demos/saltwind.html" target="_blank" rel="noopener">⛵ SALTWIND 帆船竞速</a> | 绕标计时赛 | Canvas 伪 3D + 帆船极曲线 |
| <a href="/demos/muyu.html" target="_blank" rel="noopener">🪷 电子木鱼</a> | 点一下功德 +1 | SVG + Web Audio 合成 |

---

## 一、在浏览器里从零训练一个 GPT

**<a href="/demos/train-gpt.html" target="_blank" rel="noopener">▶ 打开 Demo</a>**

这个不是可视化演示，是**真的在你浏览器里训练一个神经网络**。

- 8.3 万参数，2 层 Transformer，4 头自注意力，d_model = 48，上下文 24 tokens
- 前向传播、反向传播、Adam 优化器，全部纯 JavaScript 手写，零依赖
- 字符级分词，语料是 20 首唐诗五言绝句（可切换成英文 Alice in Wonderland）

打开点「开始训练」，你会看到三件事同时发生：

**1. Loss 从 5.57 一路砸到 0.2。** 5.57 是 `ln(词表大小)`，也就是「完全瞎猜」的水平。曲线上有每步的原始 loss 和 EMA 平滑两条线，鼠标悬停可以查任意一步的具体数值。

**2. 注意力热图从糊状变得有结构。** 8 个注意力头（L1·H1 到 L2·H4）可以逐个切换查看。训练前是均匀的一片，训练后会浮现出清晰的对角条纹和竖直亮列——模型自己发现了「五个字 + 一个标点」的格律周期。悬停任意格子能看到「query『月』看 key『明』权重 34.2%」。

**3. 生成样本每 60 步刷新一次。** 从纯乱码，到学会五言断句，到背出「春眠不觉晓，处闻啼鸟。夜来风雨声，花落知多少」。温度滑块可以调，0.1 是老实背书，1.5 是胡言乱语。

大约 3000 tokens/秒，十几秒就能看到 loss 曲线跳崖式下降。

### 最大的坑：手写反向传播错了不会报错

这是整个项目里最需要强调的一点。

手写 backprop 出错时，**程序不会崩溃，不会抛异常，甚至 loss 也会下降**——只是「训练效果差一点」，肉眼根本看不出来。如果直接开始写界面，等发现模型学不好的时候，你根本不知道是超参数问题、数据问题，还是某个偏导数写错了符号。

所以正确的顺序是：**先写数值梯度校验，通过了再碰界面。**

原理是中心差分。对每个参数 `θᵢ`，把它加减一个极小量 `h`，分别跑一次前向传播算出 loss，则真实梯度约等于：

```
∂L/∂θᵢ  ≈  [ L(θᵢ + h) − L(θᵢ − h) ] / (2h)
```

拿这个「数值梯度」和你手写的「解析梯度」逐一对比，看相对误差：

```js
const h = 1e-5;
for (const name in model.P) {
  const p = model.P[name], g = model.G[name];
  for (const i of sampleIndices(p.length, 6)) {
    const orig = p[i];
    p[i] = orig + h; const lossPlus  = forwardAndLoss();
    p[i] = orig - h; const lossMinus = forwardAndLoss();
    p[i] = orig;

    const numerical = (lossPlus - lossMinus) / (2 * h);
    const analytic  = g[i];
    const relErr = Math.abs(numerical - analytic) /
                   Math.max(Math.abs(numerical) + Math.abs(analytic), 1e-8);
    // relErr 必须在 1e-4 以下，最好到 1e-6 量级
  }
}
```

实际跑出来的结果：

```
loss = 2.359003 (期望 ≈ ln(11) = 2.398)   params = 1976
worst relative error: 2.328e-6 @ wqkv_0[80]
GRADCHECK PASS
after 200 steps on fixed batch: loss = 0.0031
OVERFIT PASS
```

最大相对误差 `2.3e-6`，已经是浮点数噪声的水平了，说明 LayerNorm、softmax、注意力、GELU 这几处的反向传播全部正确。

第二个检查同样重要：**在一个固定的小批次上能否过拟合到 loss ≈ 0**。如果反向传播有错，模型是没法把一个固定输入背下来的。200 步降到 0.0031，通过。

这两项都过了，才开始写 UI。

### 关于结构

模型核心大约 300 行，结构和真实的 GPT 完全一致，只是尺寸小了七个数量级：

```
token embedding + position embedding
  ↓
× 2 层 {
    LayerNorm → 多头因果自注意力 → 残差
    LayerNorm → MLP(4×宽, GELU)  → 残差
  }
  ↓
LayerNorm → 输出投影到词表 → softmax 交叉熵
```

所有权重存在扁平的 `Float64Array` 里，矩阵乘法手写三重循环。这个规模下性能完全够用——真正的瓶颈反而是 UI 重绘，所以训练是按「每帧 N 步」的节奏跑的，不阻塞页面。

---

## 二、The Clocktower Fell Silent：手写 WebGL 引擎

**<a href="/demos/clocktower.html" target="_blank" rel="noopener">▶ 打开 Demo</a>**

一个第一人称探索小游戏：钟楼停摆了，循着蓝色风铃找回 6 颗消失的「秒」，让大钟重新鸣响。

因为不能外链 Three.js，整个 3D 引擎是从零写的：

- **矩阵数学**：透视投影矩阵、平移/旋转/缩放矩阵、4×4 矩阵乘法
- **着色器**：顶点着色器 + 片元着色器，平面着色（flat shading）光照模型
- **雾效**：指数平方雾，让远景融进暖橙色天光里
- **几何生成器**：房子、秋树、山丘、钟楼全是代码程序化生成的，不是模型文件

低多边形的树是这么来的——取一个正二十面体，把每个顶点随机抖动一下，再给每个面染上略有差异的颜色：

```js
const IT = (1 + Math.sqrt(5)) / 2;              // 黄金比例
const IV = [[-1,IT,0],[1,IT,0], /* …12 个顶点 */].map(normalize);
const IF = [[0,11,5],[0,5,1],  /* …20 个面   */];

function blob(cx, cy, cz, sx, sy, sz, col) {
  const pts = IV.map(p => [
    cx + p[0] * sx * (0.9 + rnd() * 0.2),       // 顶点随机抖动
    cy + p[1] * sy * (0.9 + rnd() * 0.2),
    cz + p[2] * sz * (0.9 + rnd() * 0.2),
  ]);
  for (const f of IF) tri(pts[f[0]], pts[f[1]], pts[f[2]], jitter(col));
}
```

平面着色的关键是：**不要共享顶点**。每个三角形写自己的三份顶点，法线按面算，这样相邻面之间就有硬边，出来才是低多边形那种切面感，而不是圆滑的球。

开场是一段电影镜头绕村庄缓缓推进，用平滑插值把摄像机从空中拉到玩家视角。按 Enter 可以跳过。操作是点击锁定视角 + WASD 移动，手机上左半屏移动、右半屏转视角。

---

## 三、SALTWIND：真实的帆船物理

**<a href="/demos/saltwind.html" target="_blank" rel="noopener">▶ 打开 Demo</a>**

Canvas 伪 3D 海面上的绕标计时赛，7 道红绿浮标门。

有意思的地方在于它用了真实的**帆船极曲线**（polar diagram）建模。帆船最反直觉的一点是：**顺风不是最快的**。船速取决于船头和风向的夹角：

| 风向角 | 状态 | 相对速度 |
| --- | --- | --- |
| 0–30° | In irons（顶风） | ≈ 0，船会停 |
| 45° | Close hauled（抢风） | 0.6 |
| 90° | Beam reach（横风） | 1.0 |
| 120° | Broad reach（侧顺风） | **1.05（最快）** |
| 180° | Running（正顺风） | 0.72 |

```js
const polarPts = [[0,0],[30,0.12],[45,0.6],[60,0.85],
                  [90,1.0],[120,1.05],[150,0.9],[180,0.72]];
```

所以逆风想往前走，必须走「之」字形抢风换舷（tacking）——这是真实帆船比赛的核心技巧，游戏里也必须这么开。

另外帆角要贴住 HUD 上的绿色最优刻度才能吃满风，偏了会掉速并提示 `SHEET IN · PRESS S`。蓄满的空格阵风给一段爆发加速。

---

## 四、电子木鱼

**<a href="/demos/muyu.html" target="_blank" rel="noopener">▶ 打开 Demo</a>**

最轻松的一个：点一下功德 +1，敲到 108 下解锁「烦恼尽消」，1000 下「在线成佛」。

值得一提的是那声「笃」——**没有用任何音频文件**，是 Web Audio 现场合成的。木鱼的音色 = 一段短促的噪声爆发（敲击的「哒」）+ 三个衰减正弦波（木头腔体的共鸣）：

```js
// 1. 噪声爆发 → 带通滤波 = 木头的敲击声
const buf = actx.createBuffer(1, actx.sampleRate * 0.16, actx.sampleRate);
const d = buf.getChannelData(0);
for (let i = 0; i < d.length; i++) {
  d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 5);
}
const bp = actx.createBiquadFilter();
bp.type = 'bandpass'; bp.frequency.value = 950; bp.Q.value = 3.2;

// 2. 三个衰减正弦 = 腔体共鸣，每次随机微调音高避免机械感
const detune = 1 + (Math.random() - 0.5) * 0.05;
for (const [f, amp, dur] of [[188, 0.34, 0.34], [372, 0.13, 0.2], [710, 0.05, 0.12]]) {
  // triangle 波 + 指数衰减包络
}
```

每次敲击给音高加一点随机偏移，连续敲的时候才不会听起来像机器。

---

## 写在最后

这组 Demo 想说明的是：**「零依赖」不等于「做不了复杂的东西」**。

浏览器原生提供的 WebGL、Canvas、Web Audio、`Float64Array`，能力边界比大多数人以为的要宽。当然日常开发该用库还是要用库——但亲手写一遍投影矩阵和反向传播，对理解这些库到底在替你做什么，帮助是不可替代的。

尤其是那个 GPT：把 Transformer 的每一个偏导数亲手推一遍、再用数值梯度验证一遍，比读十篇讲注意力机制的文章都管用。

所有源码都在仓库的 `.vuepress/public/demos/` 目录下，也可以在任意 Demo 页面右键「查看网页源代码」直接读。

👉 **<a href="/demos/" target="_blank" rel="noopener">打开 Demo 合集页</a>**
