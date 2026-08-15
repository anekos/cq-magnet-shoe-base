"""壁付けマグネット・シューベース.

ライト側の 18x18x2mm プレートを上から落とし込んで保持する。
ライトは壁に対して垂直（手前）に張り出し、自重で溝の底に着座する。

構成:
    80mm 角の平板の四隅に磁石を埋め、溝は平板そのものに彫り込む（島は立てない）。
    溝は平板の上端まで抜けている。閉じると溝の天井がオーバーハングになるうえ、
    そもそも上端が開いていないとライトを差し込めない。

座標系:
    X = 壁に沿う左右（0 が中心）
    Y = 壁から手前へ（Y=0 が壁との接触面）
    Z = 上下（Z=0 が底面）

印刷方向:
    既定は縦置き（背板を立てて Z 方向に積層＝モデル座標のまま）。
    溝は垂直な押し出しになるのでオーバーハングが一切なく、はめあいが正確に出る。
    横向きになる磁石穴だけが天井を持つので、ティアドロップ形状で 45 度に逃がす。
    接地面が 80 x plate_t と細いため、ブリム推奨。
    lay_flat=True にすると背面をベッドに寝かせた向きで出力する（要サポートなし、
    ただしリップ下面が 1.65mm のオーバーハングになる）。
"""

import math

import cadquery as cq
from click_cadquery.git import version_number as ver
from pydantic import BaseModel


class Param(BaseModel):
    # --- 背板 ---
    plate_w: float = 80.0  # 背板の幅
    plate_h: float = 80.0  # 背板の高さ
    corner_r: float = 5.0  # 四隅の丸め

    # --- ライト側プレートの実測値 ---
    foot_w: float = 18.0  # プレート幅
    foot_t: float = 2.0  # プレート厚
    foot_l: float = 18.0  # プレート長（差し込み方向）
    neck_w: float = 12.0  # プレートとライト本体をつなぐ首の幅

    # --- はめあいクリアランス（gauge を印刷して実物で確認済み） ---
    fit_x: float = 0.5  # 幅方向の総クリアランス
    fit_y: float = 0.3  # 厚み方向の総クリアランス
    fit_z: float = 1.0  # 差し込み方向の余裕
    fit_mouth: float = 2.0  # 首まわりの総クリアランス。首の実測が甘いので広め
    #                         開口を広げても減るのは掴み代だけ

    # --- 溝 ---
    lip_t: float = 2.0  # リップの肉厚（表面側）
    floor_t: float = 2.0  # 溝の床の背後に残す肉厚（壁側）
    seat_drop: float = 0.0  # 着座位置を上端から下げる量。溝はその分だけ長く開く
    edge_chamfer: float = 0.8  # 上端の面取り。兼、プレート挿入時のガイド
    lip_chamfer: float = 0.6  # リップ下面の逃がし。lay_flat で寝かせるとき用

    # --- 磁石（四隅に 4 個） ---
    mag_d: float = 15.0  # ネオジム磁石 直径
    mag_t: float = 3.0  # ネオジム磁石 厚み
    mag_fit: float = 0.3  # 接着剤用クリアランス（直径・深さとも）
    mag_wall: float = 1.7  # 磁石穴の底に残す最小肉厚
    mag_margin: float = 3.4  # 磁石穴の縁から背板の縁までの肉厚
    mag_teardrop: bool = True  # 縦置き印刷用に磁石穴の上へ 45 度の屋根を足す

    # --- 出力 ---
    lay_flat: bool = False  # True なら背面をベッドに寝かせた向きで出力する

    # --- はめあい確認用の小片 ---
    gauge: bool = False  # True なら磁石穴なしの小さな試し刷りを出力する
    gauge_h: float = 12.0  # そのときの溝の高さ
    gauge_stop: float = 4.0  # そのとき溝の下に残す中実部
    side_wall: float = 3.4  # そのとき溝の左右に残す肉厚

    @property
    def slot_w(self) -> float:
        """溝の内寸幅."""
        return self.foot_w + self.fit_x

    @property
    def slot_d(self) -> float:
        """床面からリップ下面までの深さ."""
        return self.foot_t + self.fit_y

    @property
    def mouth_w(self) -> float:
        """リップ間の開口幅."""
        return self.neck_w + self.fit_mouth

    @property
    def lip_grip(self) -> float:
        """リップがプレートを掴む量（片側）."""
        return (self.slot_w - self.mouth_w) / 2

    @property
    def plate_t(self) -> float:
        """背板の厚み. 溝の必要厚と磁石の必要厚の大きいほう."""
        return max(
            self.floor_t + self.slot_d + self.lip_t,
            self.mag_hole_depth + self.mag_wall,
        )

    @property
    def channel_h(self) -> float:
        """溝の高さ. 上端から掘り下げる."""
        return self.foot_l + self.fit_z + self.seat_drop

    @property
    def channel_z(self) -> float:
        """溝の下端（＝ライトが着座する面）."""
        return self.plate_h - self.channel_h

    @property
    def mag_hole_d(self) -> float:
        return self.mag_d + self.mag_fit

    @property
    def mag_hole_depth(self) -> float:
        return self.mag_t + self.mag_fit

    @property
    def mag_r(self) -> float:
        return self.mag_hole_d / 2

    @property
    def mag_peak(self) -> float:
        """磁石穴の中心から穴の最上点まで. ティアドロップの尖りぶん高くなる."""
        return self.mag_r * math.sqrt(2) if self.mag_teardrop else self.mag_r

    @property
    def mag_positions(self) -> list[tuple[float, float]]:
        """磁石中心の (X, Z). 四隅. 上側はティアドロップの尖りぶん下げる."""
        x = self.plate_w / 2 - (self.mag_margin + self.mag_r)
        z_lo = self.mag_margin + self.mag_r
        z_hi = self.plate_h - (self.mag_margin + self.mag_peak)
        return [(sx * x, z) for sx in (-1, 1) for z in (z_lo, z_hi)]

    @property
    def mag_pitch_z(self) -> float:
        """上下の磁石の間隔."""
        zs = sorted({z for _, z in self.mag_positions})
        return zs[-1] - zs[0]

    @property
    def filename(self) -> str:
        kind = "gauge" if self.gauge else "base"
        drop = f"-drop{self.seat_drop:g}" if self.seat_drop else ""
        flat = "-flat" if self.lay_flat else ""
        return (
            f"v{ver()}-{kind}-{self.plate_w:g}x{self.plate_h:g}{drop}{flat}"
            f"-foot{self.foot_w:g}x{self.foot_t:g}-neck{self.neck_w:g}"
            f"-mag{self.mag_d:g}x{self.mag_t:g}.stl"
        )


def _box(w: float, d: float, h: float, y: float = 0.0, z: float = 0.0) -> cq.Workplane:
    """X 中心・Y/Z は指定値を最小側とする直方体."""
    return (
        cq.Workplane("XY")
        .box(w, d, h, centered=(True, False, False))
        .translate((0, y, z))
    )


def _plate(param: Param) -> cq.Workplane:
    plate = _box(param.plate_w, param.plate_t, param.plate_h)
    if param.corner_r > 0:
        plate = plate.edges("|Y").fillet(param.corner_r)
    return plate


def _magnet_cups(param: Param) -> cq.Workplane:
    """背面（Y=0）から掘る磁石のザグリ穴.

    縦置きで印刷すると横向きの穴になり天井ができるので、ティアドロップ
    （円の上に 45 度の屋根）にして垂れを防ぐ。屋根の中は空くだけで、
    磁石は円の部分に収まる。
    """
    r = param.mag_r
    depth = param.mag_hole_depth

    profile = cq.Workplane("XY").circle(r).extrude(-depth)
    if param.mag_teardrop:
        k = r / math.sqrt(2)  # 45 度の接点
        roof = (
            cq.Workplane("XY")
            .polyline([(-k, k), (k, k), (0, param.mag_peak)])
            .close()
            .extrude(-depth)
        )
        profile = profile.union(roof)
    # 手前（-Z 側）に押し出した形状を +Y 向きに起こす。スケッチの +Y が +Z になる
    profile = profile.rotate((0, 0, 0), (1, 0, 0), 90)

    cups = cq.Workplane("XY")
    for x, z in param.mag_positions:
        cups = cups.union(profile.translate((x, 0, z)))
    return cups


def _lip_reliefs(param: Param) -> cq.Workplane:
    """リップ下面のオーバーハングを 45 度に逃がす三角柱（左右）.

    lay_flat で寝かせて印刷するとき用。縦置きなら不要だが、付いていても
    はめあいに効くのは掴み代が 0.6mm 減ることだけなので常に入れておく。
    """
    x0 = param.mouth_w / 2
    y0 = param.floor_t + param.slot_d
    c = param.lip_chamfer
    tri = (
        cq.Workplane("XY")
        .polyline([(x0, y0), (x0 + c, y0), (x0, y0 + c)])
        .close()
        .extrude(param.channel_h)
        .translate((0, 0, param.channel_z))
    )
    return tri.union(tri.mirror("YZ"))


def _channel(param: Param) -> cq.Workplane:
    """溝. プレートが入る幅広部と、首を逃がす開口部. 上端まで抜く."""
    cut = _box(
        param.slot_w,
        param.slot_d,
        param.channel_h,
        y=param.floor_t,
        z=param.channel_z,
    )
    cut = cut.union(
        _box(
            param.mouth_w,
            param.plate_t - param.floor_t,
            param.channel_h,
            y=param.floor_t,
            z=param.channel_z,
        )
    )
    if param.lip_chamfer > 0:
        cut = cut.union(_lip_reliefs(param))
    return cut


def _lay_flat(result: cq.Workplane) -> cq.Workplane:
    """背面をベッドに接地させ、原点まわりに置く（壁の +Y を +Z に倒す）."""
    flat = result.rotate((0, 0, 0), (1, 0, 0), 90)
    shape = flat.val()
    assert isinstance(shape, cq.Shape)  # 実体は Solid
    bb = shape.BoundingBox()
    return flat.translate((0, -(bb.ymin + bb.ylen / 2), -bb.zmin))


def build(param: Param) -> cq.Workplane:
    result = _build(param)
    return _lay_flat(result) if param.lay_flat else result


def _build(param: Param) -> cq.Workplane:
    if param.gauge:
        # はめあい確認用: 溝のまわりだけを残した小片。磁石は省く
        param = param.model_copy(
            update={
                "plate_w": param.slot_w + 2 * param.side_wall,
                "plate_h": param.gauge_h + param.gauge_stop,
                "corner_r": 2.0,
                "seat_drop": param.gauge_h - (param.foot_l + param.fit_z),
            }
        )
        result = _plate(param).cut(_channel(param))
    else:
        result = _plate(param).cut(_magnet_cups(param)).cut(_channel(param))

    # 上端: 外周と溝の開口を同時に面取りして挿入ガイドにする
    return result.faces(">Z").edges().chamfer(param.edge_chamfer)
