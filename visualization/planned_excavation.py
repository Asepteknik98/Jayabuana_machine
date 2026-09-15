"""Render engine-provided planned bounds, without conflict calculations."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen

from adapters.sensor_source import SafeDigState
from modules.safedig_precision.design_conflict import ConflictStatus
from modules.safedig_precision.bucket_position import PIXELS_PER_METRE
from visualization.excavator_2d import SCENE_WIDTH,SCENE_HEIGHT
from visualization.underground_utility import world_to_scene


def draw_planned_excavation(painter: QPainter,bounds: QRectF,state: SafeDigState) -> None:
    result=state.design_conflict
    if result is None or result.left_x_m is None:
        return
    painter.save()
    scale=min(bounds.width()/SCENE_WIDTH,bounds.height()/SCENE_HEIGHT)
    painter.translate(bounds.center());painter.scale(scale,scale)
    painter.translate(-SCENE_WIDTH/2,-SCENE_HEIGHT/2)
    rect=QRectF(world_to_scene(result.left_x_m,0),world_to_scene(result.right_x_m,result.bottom_z_m))
    color=QColor({ConflictStatus.NO_CONFLICT:'#68deeb',ConflictStatus.POTENTIAL_CONFLICT:'#ffb347',
                  ConflictStatus.DESIGN_CONFLICT:'#ff6060',ConflictStatus.UNKNOWN:'#a1adba'}[result.status])
    painter.setPen(QPen(color,1.5,Qt.PenStyle.DashLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(rect)
    envelope=state.envelope
    if result.valid and result.planned_clearance_m is not None and result.planned_clearance_m <= 0 and envelope is not None and envelope.valid:
        trench=QPainterPath();trench.addRect(rect)
        zone=QPainterPath()
        radius=envelope.effective_clearance_m*PIXELS_PER_METRE
        zone.addEllipse(world_to_scene(envelope.center_x_m,envelope.center_z_m),radius,radius)
        fill=QColor(color);fill.setAlpha(45)
        painter.fillPath(trench.intersected(zone),fill)
    font=painter.font();font.setPixelSize(12);painter.setFont(font)
    painter.drawText(rect.bottomLeft()+QPointF(0,18),f'TARGET {-result.bottom_z_m:.2f} m')
    painter.restore()
