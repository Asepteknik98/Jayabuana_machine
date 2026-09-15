"""Draw source-neutral envelope geometry and informational measurements."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from core.safe_envelope import EnvelopeState, EnvelopeStatus
from modules.safedig_precision.bucket_position import PIXELS_PER_METRE
from visualization.excavator_2d import SCENE_WIDTH, SCENE_HEIGHT
from visualization.underground_utility import world_to_scene

COLORS = {EnvelopeStatus.CLEAR: "#59dbc5", EnvelopeStatus.APPROACHING: "#ffb347",
          EnvelopeStatus.INSIDE: "#ff6060", EnvelopeStatus.UNAVAILABLE: "#a1adba"}


def draw_safe_envelope(painter: QPainter, bounds: QRectF, envelope: EnvelopeState, presentation=False) -> None:
    painter.save()
    scale = min(bounds.width() / SCENE_WIDTH, bounds.height() / SCENE_HEIGHT)
    painter.translate(bounds.center())
    painter.scale(scale, scale)
    painter.translate(-SCENE_WIDTH / 2, -SCENE_HEIGHT / 2)
    color = QColor(COLORS[envelope.status])
    if envelope.valid:
        center = world_to_scene(envelope.center_x_m, envelope.center_z_m)
        radius = envelope.effective_clearance_m * PIXELS_PER_METRE
        fill = QColor(color)
        fill.setAlpha(45)
        painter.setBrush(fill)
        painter.setPen(QPen(color, 2))
        painter.drawEllipse(center, radius, radius)
    if presentation:
        painter.setPen(color)
        font=painter.font();font.setPixelSize(15);painter.setFont(font)
        painter.drawText(QPointF(28,45),"SAFE ENVELOPE / "+envelope.status.value)
        painter.restore();return
    # No zone at a fabricated location when unavailable; show a gray legend.
    painter.setBrush(QColor("#0b1d2e"))
    painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine if not envelope.valid else Qt.PenStyle.SolidLine))
    painter.drawRect(QRectF(405, 20, 380, 135))
    font = painter.font()
    font.setPixelSize(13)
    painter.setFont(font)
    if envelope.valid:
        lines = ["DYNAMIC SAFE ENVELOPE â€¢ PROTOTYPE",
                 f"ENVELOPE {envelope.status.value}  (utility center)",
                 f"Safe Clearance: {envelope.base_clearance_m:.2f} m | Uncertainty: {envelope.uncertainty_margin_m:.3f} m",
                 f"Effective Envelope: {envelope.effective_clearance_m:.3f} m",
                 f"Bucket Distance: {envelope.distance_to_utility_m:.2f} m",
                 f"Clearance Margin: {envelope.clearance_margin_m:+.2f} m"]
    else:
        lines = ["DYNAMIC SAFE ENVELOPE â€¢ PROTOTYPE", "ENVELOPE UNAVAILABLE", envelope.information]
    for row, text in enumerate(lines):
        painter.drawText(QPointF(415, 40 + row * 20), text)
    painter.restore()
