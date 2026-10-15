"""SVG is a view of exported geometry, with no remote assets or drawing model."""
from html import escape

from shapely.geometry import Polygon

from .models import Brief, Layout, Report

COLORS = {"reception":"#e8f0ff", "workroom":"#dff1ef", "office":"#f0ecfa", "meeting":"#fff0d9"}


def svg_export(brief: Brief, layout: Layout, report: Report) -> str:
    w,h = brief.floor.width_mm,brief.floor.depth_mm
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1150 -1250 {w+2300} {h+2600}" role="img" aria-labelledby="planTitle planDesc">',
           f'<title id="planTitle">{escape(brief.project_name)} — dimensioned office floor plan</title>',
           '<desc id="planDesc">Dimensions in metres. Indicative furniture. Independent geometry checks only; architectural, operational and regulatory review remains unverified.</desc>',
           '<style>text{font-family:Arial,sans-serif;fill:#27354a} .dim{font-size:200px;fill:#67768b} .space-name{font-size:225px;font-weight:600} .room-info{font-size:180px;fill:#53647a} .furn{fill:#fff;fill-opacity:.8;stroke:#8193a3;stroke-width:16} .wall{fill:#34435a} .threshold{fill:#e6c781} .outline{fill:none;stroke:#98a5b5;stroke-width:12} g[data-room]{cursor:pointer;outline:none} g[data-room]:focus .room-fill,g[data-room].selected .room-fill{stroke:#2863eb;stroke-width:45} </style>',
           f'<rect x="-1150" y="-1250" width="{w+2300}" height="{h+2600}" fill="#fff"/>']

    def polygon(item, cls="", fill=None):
        pts=" ".join(f"{x},{y}" for x,y in item.polygon)
        return f'<polygon points="{pts}" class="{cls}"'+(f' fill="{fill}"' if fill else '')+'/>'

    for room in layout.rooms:
        out.append(f'<g data-room="{escape(room.id,quote=True)}" tabindex="0" role="button" aria-label="Inspect {escape(room.name,quote=True)}">')
        out.append(polygon(room,"room-fill",COLORS[room.kind]))
        for furn in layout.furniture:
            if furn.room_id == room.id:
                out.append(polygon(furn,"furn"))
        p=Polygon(room.polygon)
        x1,y1,x2,y2=p.bounds
        cx=(x1+x2)/2
        cy=y2-600 if y2 <= brief.fixed.corridor.y1 else y1+380
        out.extend([f'<text x="{cx}" y="{cy}" text-anchor="middle" class="space-name">{escape(room.name)}</text>',
                    f'<text x="{cx}" y="{cy+260}" text-anchor="middle" class="room-info">{p.area/1e6:.2f} m² · {(x2-x1)/1000:.2f} × {(y2-y1)/1000:.2f} m</text>', '</g>'])
    out.append(polygon(layout.corridor,fill="#f1f4f8"))
    cp=Polygon(layout.corridor.polygon)
    cx,cy=cp.centroid.coords[0]
    out.append(f'<text x="{cx}" y="{cy+75}" text-anchor="middle" class="dim">CIRCULATION · {(cp.bounds[3]-cp.bounds[1])/1000:.2f} m CLEAR</text>')
    out.append(polygon(layout.core,fill="#e9edf2"))
    core=Polygon(layout.core.polygon)
    cx,cy=core.centroid.coords[0]
    out.extend([f'<text x="{cx}" y="{cy-50}" text-anchor="middle" class="space-name">Service reserve</text>',f'<text x="{cx}" y="{cy+240}" text-anchor="middle" class="room-info">{core.area/1e6:.2f} m² gross reserve</text>'])
    out.extend(polygon(wall,"wall") for wall in layout.walls)
    for door in layout.doors:
        out.append(polygon(door,"threshold"))
        x1,y1,x2,y2=Polygon(door.polygon).bounds
        if y2-y1>x2-x1:
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x1+min(350,y2-y1)}" y2="{y1}" stroke="#8b713d" stroke-width="20"/>')
        else:
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y1+min(350,x2-x1)}" stroke="#8b713d" stroke-width="20"/>')
    # Overall dimensions use actual outside shell, not room totals.
    out.extend([f'<path d="M 0,-200 V -680 H {w} V -200 M 0,-760 V -580 M {w},-760 V -580" class="outline"/>',
                f'<text x="{w/2}" y="-830" text-anchor="middle" class="dim">{w/1000:.2f} m OUTSIDE</text>',
                f'<path d="M {w+200},0 H {w+640} V {h} H {w+200} M {w+550},0 H {w+730} M {w+550},{h} H {w+730}" class="outline"/>',
                f'<text x="{w+930}" y="{h/2}" text-anchor="middle" transform="rotate(90 {w+930} {h/2})" class="dim">{h/1000:.2f} m OUTSIDE</text>',
                f'<text x="0" y="{h+650}" class="dim">{brief.rules.grid_mm} mm design grid · dimensions in metres · revision {brief.revision} · indicative furniture</text>',
                f'<text x="0" y="{h+1000}" class="dim">Geometry {report.validation_status.upper()} within declared scope · architectural and regulatory review UNVERIFIED</text>', '</svg>'])
    return "".join(out)
