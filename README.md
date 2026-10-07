# Cornell Box Ray Tracing

Python 3.10 以降の標準ライブラリだけで動作する CPU パストレーサーです。
赤と緑の壁、白い床・天井・奥壁、回転した大小の箱、天井の面光源を描画します。
拡散反射の間接照明、面光源のサンプリングによる柔らかい影、アンチエイリアシング、
ロシアンルーレット、トーンマッピングに対応しています。

```sh
python3 render.py
```

画像は `output/cornell.png` に出力されます。外部パッケージや GPU は不要です。

短時間で確認する場合:

```sh
python3 render.py --width 64 --height 64 --samples 4
```

高品質な画像を作成する場合（CPU では時間がかかります）:

```sh
python3 render.py --width 512 --height 512 --samples 128 --depth 12 --output output/high.png
```

`--samples` は画素あたりのサンプル数です。増やすほどノイズが減ります。
`--depth` は最大反射回数、`--seed` は乱数シードです。同じ引数で画像を再現できます。
すべてのマテリアルは拡散反射です。鏡面反射や屈折は実装していません。

検証:

```sh
python3 -m unittest discover -s tests -v
```
