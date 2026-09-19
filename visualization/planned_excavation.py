"""Render engine-provided planned bounds, without conflict calculations."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen

from adapters.sensor_source import SafeDigState
from modules.safedig_precision.design_conflict import ConflictStatus
from modules.safedig_precision.bucket_position import PIXELS_PER_METRE
from visualization.excavator_2d import SCENE_WIDTH,SCENE_HEIGHT
from visualization.underground_utility import world_to_scene


def draw_planned_excavation(painter: QPainter,bounds: QRectF,state: SafeDigState, presentation=False) -> None:
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
    painter.setPen(QPen(QColor("#e4ecf4") if presentation else color,1.5,Qt.PenStyle.DashLine))
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
    if presentation:
        # Label sizing and placement are presentation-only; world geometry above is unchanged.
        font.setPixelSize(max(15,round(13/max(scale,.01))));painter.setFont(font)
        def callout(y,caption,value,anchor,accent):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            box=QRectF(640,y,144,56)
            painter.setPen(QPen(QColor("#b9cbd8"),1,Qt.PenStyle.DashLine))
            painter.drawLine(anchor,QPointF(628,anchor.y()))
            painter.drawLine(QPointF(628,anchor.y()),QPointF(628,y+28))
            painter.drawLine(QPointF(628,y+28),QPointF(640,y+28))
            painter.setPen(QPen(QColor("#426277"),1));painter.setBrush(QColor(6,24,38,240))
            painter.drawRoundedRect(box,5,5)
            painter.setPen(QPen(QColor(accent),2));painter.drawLine(QPointF(640,y+9),QPointF(640,y+47))
            painter.setPen(QColor("#bfd0de"));painter.drawText(QPointF(650,y+20),caption)
            value_font=painter.font();value_font.setPixelSize(max(22,round(18/max(scale,.01))));value_font.setBold(True);painter.setFont(value_font)
            painter.setPen(QColor("#eff8ff"));painter.drawText(QPointF(650,y+45),f"{value:.2f} m")
            painter.restore()
        callout(448,"Target Depth",-result.bottom_z_m,rect.bottomRight(),"#dce8f1")
        if state.machine and state.machine.current_depth_m is not None:
            machine=state.machine
            callout(354,"Current Depth",machine.current_depth_m,world_to_scene(machine.bucket_x_m,machine.bucket_z_m),"#65d9ee")
    else:painter.drawText(rect.bottomLeft()+QPointF(0,18),f'TARGET {-result.bottom_z_m:.2f} m')
    painter.restore()
