"use strict";

const state = {brief:null, result:null, step:0, view:"brief", tab:"plan", busy:false, fixedExpanded:false, dimensionMode:"known", selected:"meeting"};
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = (value, digits=2) => Number(value).toFixed(digits);
const clone = value => JSON.parse(JSON.stringify(value));
const metres = value => value == null ? "" : Number((value/1000).toFixed(3));
const kinds = {reception:"Reception & waiting",workroom:"Shared workstations",office:"Private workstation",meeting:"Meeting & collaboration"};
const colors = {reception:"#e8f0ff",workroom:"#dff1ef",office:"#f0ecfa",meeting:"#fff0d9"};
let waitingTimer = null;

function showNotice(message, error=false) {
  const node = $("#notice");
  node.hidden = !message;
  node.className = "notice" + (error ? " error" : "");
  node.textContent = message || "";
}

function fieldsError(data) {
  showNotice(data.message || "Review the indicated fields.", true);
  if (Array.isArray(data.errors)) {
    const ul=document.createElement("ul");
    data.errors.forEach(e => {
      const li=document.createElement("li");
      li.textContent=e.field + ": " + e.message;
      ul.appendChild(li);
    });
    $("#notice").appendChild(ul);
  }
}

function input(path, title, value, {mm=false, min=0, step="any", suffix="", required=true, type="number", help=""}={}) {
  let control='<input data-path="'+esc(path)+'" '+(mm?'data-mm ':'')+'type="'+type+'" value="'+esc(mm?metres(value):value)+'"';
  if (type === "number") control+=' min="'+min+'" step="'+step+'"';
  if (required) control+=" required";
  control+=' aria-label="'+esc(title)+'">';
  if (suffix) control='<span class="input-suffix">'+control+'<span>'+suffix+'</span></span>';
  return '<label><span class="field-label">'+esc(title)+'</span>'+control+(help?'<span class="field-help">'+esc(help)+'</span>':"")+'</label>';
}

function option(value, label, selected) {
  return '<option value="'+esc(value)+'"'+(String(value)===String(selected)?" selected":"")+'>'+esc(label)+'</option>';
}

function select(path,title,value,options,control=false,help="") {
  return '<label><span class="field-label">'+title+'</span><select '+(control?'data-control="':'data-path="')+esc(path)+'" aria-label="'+esc(title)+'">'+options.map(v=>option(v[0],v[1],value)).join("")+'</select>'+(help?'<span class="field-help">'+help+'</span>':"")+'</label>';
}

function setPath(path,value) {
  const parts=path.split(".");
  let node=state.brief;
  for (const part of parts.slice(0,-1)) node=node[part];
  node[parts[parts.length-1]]=value;
}

function invalidate(message) {
  if (!state.brief) return;
  state.brief.revision+=1;
  state.result=null;
  $("#downloadJson").disabled=true;
  $("#downloadSvg").disabled=true;
  if (state.view==="result" && !state.busy) renderResult();
  updateSummary();
  if (message) showNotice(message);
  const json=$("#briefJson");
  if(json) json.textContent=JSON.stringify(state.brief,null,2);
}

function updateSummary() {
  const b=state.brief;
  if(!b) return;
  $("#projectBreadcrumb").textContent=b.project_name || "Untitled office";
  $("#grossMetric").innerHTML=fmt(b.floor.width_mm*b.floor.depth_mm/1e6)+' <small>m²</small>';
  const staff=b.rooms.filter(r=>r.kind!=="meeting").reduce((n,r)=>n+r.capacity,0);
  $("#staffMetric").textContent=staff;
  $("#meetingMetric").innerHTML=(b.rooms.find(r=>r.kind==="meeting")?.capacity || 0)+' <small>seats</small>';
  const badge=$("#revisionBadge");
  const passed=state.result?.validation_status==="passed";
  const conflict=state.result && !passed;
  badge.className="status-badge "+(passed?"passed":conflict?"warning":"draft");
  badge.textContent=(state.busy?"Generating":passed?"Geometry checked":conflict?state.result.search_status==="infeasible"?"Conflict established":state.result.search_status:"Draft")+" · revision "+b.revision;
  renderPreview();
}

function renderPreview() {
  const b=state.brief, f=b.floor, c=b.fixed.corridor, core=b.fixed.core;
  const w=f.width_mm || 16000, h=f.depth_mm || 10000;
  const rect=(r,fill)=>'<rect x="'+r.x1+'" y="'+r.y1+'" width="'+Math.max(0,r.x2-r.x1)+'" height="'+Math.max(0,r.y2-r.y1)+'" fill="'+fill+'"/>';
  $("#boundaryPreview").innerHTML='<svg viewBox="-800 -700 '+(w+1600)+' '+(h+1400)+'" role="img" aria-label="Input boundary, fixed corridor and service reserve; no room layout yet"><rect x="0" y="0" width="'+w+'" height="'+h+'" fill="#f9fbfd" stroke="#a6b6cb" stroke-width="100"/>'+rect(c,"#e5eaf3")+rect(core,"#bac5d3")+'<text x="'+w/2+'" y="-230" text-anchor="middle" font-family="Arial,sans-serif" font-size="440" fill="#7b90ad">'+fmt(w/1000,2)+' m</text><text x="'+w/2+'" y="'+(h+630)+'" text-anchor="middle" font-family="Arial,sans-serif" font-size="400" fill="#8fa0b6">'+fmt(h/1000,2)+' m deep · '+esc(f.source_status)+' boundary</text></svg>';
  $("#geometrySummary").textContent="Input geometry only. Fixed coordinates are retained when you change the footprint.";
}

function renderStep() {
  const b=state.brief;
  if(!b) return;
  document.querySelectorAll(".step").forEach(n=>{
    n.classList.toggle("active",Number(n.dataset.step)===state.step);
    n.setAttribute("aria-current",Number(n.dataset.step)===state.step?"step":"false");
  });
  $("#backButton").hidden=state.step===0;
  $("#continueButton").hidden=state.step===2;
  $("#generateButton").hidden=state.step!==2;
  $("#stepCounter").textContent="Step "+(state.step+1)+" of 3";
  const target=$("#stepContent");
  if(state.step===0) {
    const count=b.rooms.filter(r=>r.kind==="office").length;
    const work=b.rooms.find(r=>r.kind==="workroom"), meeting=b.rooms.find(r=>r.kind==="meeting");
    let geometryFields="";
    if(state.dimensionMode==="known") {
      geometryFields=input("floor.width_mm","Outside width",b.floor.width_mm,{mm:true,min:.1,step:.001,suffix:"m"})+
        input("floor.depth_mm","Outside depth",b.floor.depth_mm,{mm:true,min:.1,step:.001,suffix:"m"});
    } else {
      geometryFields='<label><span class="field-label">Known outside area</span><span class="input-suffix"><input id="knownArea" type="number" min=".1" step=".01" placeholder="160" aria-label="Known outside area"><span>m²</span></span></label><label><span class="field-label">Declared width / depth proportion</span><input id="declaredRatio" type="number" min=".1" step=".01" placeholder="1.60" aria-label="Declared width to depth proportion"></label><div class="full inline-note">Area alone does not determine a boundary. Supply a proportion, then explicitly adopt an assumed rectangle rounded to the 50 mm design grid.<br><button class="text-button" data-action="derive-boundary">Use approximate dimensions from this proportion</button></div>';
    }
    target.innerHTML='<h2>Tell us about the office</h2><p class="intro">Start with the footprint and the activities it needs to support. You can review every assumption before generation.</p><div class="field-grid"><div class="full">'+input("project_name","Project name",b.project_name,{type:"text"})+'</div>'+select("dimensionMode","Available boundary information",state.dimensionMode,[["known","Width and depth are known"],["area","Only area is known"]],true)+select("floor.source_status","Dimension source",b.floor.source_status,[["assumed","Assumed · design study"],["measured","Measured · survey review still needed"]])+geometryFields+'<div class="full">'+input("location","Project location (optional)",b.location||"",{type:"text",required:false,help:"Recorded for context. This prototype has no selected official regulation set."})+'</div></div><div class="form-section-title">Activities & capacity <span class="activity-note">· small furnishing catalogue</span></div><div class="field-grid">'+select("officeCount","Private offices",count,[1,2,3,4].map(n=>[n,n+" private office"+(n===1?"":"s")]),true)+select("sharedCount","Shared workstations",work.capacity,[2,4,6].map(n=>[n,n+" workstations"]),true)+select("meetingCount","Meeting capacity",meeting.capacity,[4,6].map(n=>[n,n+" seats"]),true)+'<div><label><span class="field-label">Reception & waiting</span><input value="1 desk + 2 waiting seats" readonly aria-label="Reception and waiting"></label><span class="field-help">Included in the office furnishing catalogue.</span></div></div><div class="count-summary">Meeting seats can serve the same staff. They are not automatically counted as additional occupants.</div>';
  } else if(state.step===1) {
    const c=b.fixed.corridor, core=b.fixed.core;
    let coords="";
    if(state.fixedExpanded) {
      const fields=(path,r)=>'<div class="coords-grid">'+["x1","y1","x2","y2"].map(k=>input(path+"."+k,k.toUpperCase(),r[k],{mm:true,min:0,step:.001,suffix:"m"})).join("")+'</div>';
      coords='<div class="geometry-edit"><div class="inline-note">Coordinates are measured from the top-left outside corner. Editing the footprint never moves these fixed elements automatically.</div><div class="coords-heading">Corridor · inside-face clear rectangle</div>'+fields("fixed.corridor",c)+'<div class="coords-heading">Service reserve · gross reserved rectangle</div>'+fields("fixed.core",core)+b.fixed.exterior_openings.map((o,i)=>'<div class="coords-heading">Exterior aperture '+(i+1)+' <button class="text-button" data-remove-opening="'+i+'" '+(b.fixed.exterior_openings.length===1?"disabled":"")+'>Remove</button></div>'+fields("fixed.exterior_openings."+i,o)).join("")+'<div class="field-grid" style="margin-top:22px">'+input("floor.external_wall_mm","External wall",b.floor.external_wall_mm,{min:1,step:1,suffix:"mm"})+input("floor.internal_wall_mm","Internal wall",b.floor.internal_wall_mm,{min:1,step:1,suffix:"mm"})+'</div></div>';
    }
    const obstruction=b.fixed.other_obstructions.length>0;
    target.innerHTML='<h2>Keep the fixed elements fixed</h2><p class="intro">The demonstration starts from a declared corridor, service reserve and exterior apertures. These are synthetic inputs, not legal exit approvals.</p><div class="tag-row"><span class="chip">STRAIGHT CORRIDOR</span><span class="chip">END-OF-BANK CORE</span><span class="chip">RECTANGULAR ROOMS</span></div><div class="geometry-facts"><span>Corridor clear width<strong>'+fmt((c.y2-c.y1)/1000)+' m</strong></span><span>Service reserve<strong>'+fmt((core.x2-core.x1)*(core.y2-core.y1)/1e6)+' m² gross</strong></span><span>Declared walls<strong>'+b.floor.external_wall_mm+' / '+b.floor.internal_wall_mm+' mm</strong></span><span>Exterior apertures<strong>'+b.fixed.exterior_openings.length+' fixed openings</strong></span></div><button class="text-button" data-action="toggle-fixed">'+(state.fixedExpanded?"Hide":"Edit")+" fixed coordinates"+'</button>'+coords+'<div class="form-section-title">Other immovable elements</div>'+select("obstructions","Additional columns or obstructions",obstruction?"yes":"no",[["no","None in this synthetic study"],["yes","Yes · provide the fixed rectangle"]],true)+(obstruction?'<div class="inline-note">Additional interior obstructions are outside the supported family. The app will retain them and report unsupported geometry, rather than ignoring them.</div><div class="coords-grid">'+["x1","y1","x2","y2"].map(k=>input("fixed.other_obstructions.0."+k,k.toUpperCase(),b.fixed.other_obstructions[0][k],{mm:true,min:0,step:.001,suffix:"m"})).join("")+'</div>':"")+'<div style="margin-top:22px">'+input("floor.source_note","Geometry source note",b.floor.source_note,{type:"text"})+'</div>';
  } else {
    const rel=b.relationships[0];
    const sum=b.rooms.reduce((n,r)=>n+(Number(r.min_area_m2)||0),0);
    const inside=(b.floor.width_mm-2*b.floor.external_wall_mm)*(b.floor.depth_mm-2*b.floor.external_wall_mm)/1e6;
    target.innerHTML='<h2>Review the brief before generation</h2><p class="intro">Minimums and maximums are mandatory. Targets and zoning priorities are preferences. Blank maximum means no hard upper area limit.</p><div class="review-summary"><span class="chip">'+b.rooms.length+' programmed rooms</span><span class="chip">'+fmt(sum)+' m² room minimums</span><span class="chip">'+fmt(inside)+' m² inside shell</span><span class="chip">'+esc(b.floor.source_status)+' geometry</span></div><div class="table-scroll"><table class="review-table"><thead><tr><th>ROOM / ACTIVITY</th><th>MIN. m²</th><th>TARGET m²</th><th>MAX. m²</th></tr></thead><tbody>'+b.rooms.map((r,i)=>'<tr><td>'+esc(r.name)+'<small>'+r.capacity+' '+(r.kind==="meeting"?"meeting seats":r.kind==="reception"?"desk + waiting seats":"workstation"+(r.capacity===1?"":"s"))+'</small></td>'+["min_area_m2","target_area_m2","max_area_m2"].map((key,j)=>'<td><input data-path="rooms.'+i+'.'+key+'" type="number" min=".1" step=".01" '+(j<2?"required":"")+' value="'+esc(r[key]??"")+'" aria-label="'+esc(r.name)+" "+["minimum area","target area","maximum area"][j]+'"'+(j===2?' placeholder="None"':"")+'></td>').join("")+'</tr>').join("")+'</tbody></table></div>'+(sum>inside?'<div class="inline-note">The room minimums already exceed the inside shell. Generate to receive the backend’s measured contradiction and requirement IDs.</div>':"")+'<div class="form-section-title">Ranked preference</div>'+select("priority","Design priority",b.priority,[["balanced","Target areas first, then reception / workroom zoning"],["area","Target areas first, with a lighter zoning preference"],["privacy","Target areas first, then quieter private-office zoning"]])+'<details><summary>Add a room relationship</summary><p class="small muted">A shared wall is different from a direct door. Proximity is a preference, without a hard distance threshold.</p><div class="relationship-fields">'+select("relationshipKind","Relationship",rel?.kind||"none",[["none","No additional relationship"],["wall_adjacent","Mandatory shared-wall adjacency"],["door_connected","Mandatory direct doorway"],["near","Prefer nearby room centroids"]],true)+select("relationshipA","First room",rel?.a||b.rooms[0].id,b.rooms.map(r=>[r.id,r.name]),true)+select("relationshipB","Second room",rel?.b||b.rooms[1].id,b.rooms.map(r=>[r.id,r.name]),true)+'</div></details><details><summary>Inspect or edit prototype dimensional assumptions</summary><p class="small muted">These are design assumptions from PLAN.md, not verified building-code thresholds.</p><div class="field-grid" style="margin-top:15px">'+input("rules.min_short_side_mm","Minimum room short side",b.rules.min_short_side_mm,{min:1000,step:50,suffix:"mm"})+input("rules.max_aspect_ratio","Maximum room aspect ratio",b.rules.max_aspect_ratio,{min:1,step:.1})+input("rules.min_aperture_mm","Minimum aperture clear width",b.rules.min_aperture_mm,{min:600,step:50,suffix:"mm"})+input("rules.min_corridor_mm","Minimum corridor clear width",b.rules.min_corridor_mm,{min:600,step:50,suffix:"mm"})+'</div><p class="small muted">Design grid: '+b.rules.grid_mm+' mm. Geometry accuracy, door swings, accessible clearances and official regulations remain unverified.</p></details><details><summary>Inspect the structured brief</summary><pre id="briefJson"></pre><button class="text-button" data-action="download-brief">Download this brief as JSON</button></details>';
    $("#briefJson").textContent=JSON.stringify(b,null,2);
  }
  setBusyButtons();
}

function setView(view) {
  state.view=view;
  $("#briefPane").hidden=view!=="brief";
  $("#resultPane").hidden=view!=="result";
  $("#navBrief").classList.toggle("active",view==="brief");
  $("#navResult").classList.toggle("active",view==="result");
  $("#pageTitle").textContent=view==="brief"?"A clear brief. A considered layout.":"Your office, with evidence.";
  $("#pageSubtitle").textContent=view==="brief"?"Define your space, generate a plan, and inspect the evidence behind it.":"Inspect the measured geometry, explore a requirement change, and review what still needs an architect.";
  if(view==="brief") renderStep(); else {
    $("#quickMeeting").value=state.brief.rooms.find(r=>r.kind==="meeting").min_area_m2;
    renderResult();
  }
  updateSummary();
}

function blankResult(title="This revision needs a new layout", text="Generate a plan to check the current brief. Earlier results do not validate changed requirements.") {
  return '<section class="card status-card"><div class="status-icon">⌑</div><h2>'+esc(title)+'</h2><p>'+esc(text)+'</p><button class="button primary" data-action="generate">Generate this revision ↗</button></section>';
}

function reviewBanner() {
  return '<div class="review-banner"><span class="note-symbol">i</span><div><strong>Geometry checks have a defined scope.</strong> Furniture operation, door swings, accessible routes, fire/egress strategy, service-core contents and jurisdiction-specific regulations remain unverified. A qualified architect must review real-world use.</div></div>';
}

function renderInspector() {
  const result=state.result;
  if(!result?.report || !$("#inspector")) return;
  const room=result.report.room_schedule.find(r=>r.id===state.selected)||result.report.room_schedule[0];
  if(!room) return;
  state.selected=room.id;
  const furniture=result.layout.furniture.filter(f=>f.room_id===room.id);
  $("#inspector").innerHTML='<div class="inspector-title">ROOM INSPECTOR <span class="optional">· select a room</span></div><div class="room-kind">'+esc(kinds[room.kind])+'</div><h3>'+esc(room.name)+'</h3><div class="inspector-area">'+fmt(room.area_m2)+'<small>m² clear</small></div><div class="inspector-dims">'+fmt(room.width_mm/1000)+' × '+fmt(room.depth_mm/1000)+' m inside faces</div><div class="inspector-row"><span>Required minimum</span><strong>'+fmt(room.minimum_m2)+' m²</strong></div><div class="inspector-row"><span>Preferred target</span><strong>'+fmt(room.target_m2)+' m²</strong></div><div class="inspector-row"><span>Hard maximum</span><strong>'+(room.maximum_m2==null?"None":fmt(room.maximum_m2)+" m²")+'</strong></div><div class="inspector-row"><span>Activity capacity</span><strong>'+room.capacity+' '+(room.kind==="meeting"?"seats":"desk"+(room.capacity===1?"":"s"))+'</strong></div><div class="inspector-row"><span>Indicative footprints</span><strong>'+furniture.length+' items</strong></div><div class="pass-inline">✓ Area and dimensions independently measured<br>✓ Door topology and furniture footprints checked</div>';
  document.querySelectorAll("[data-room]").forEach(n=>n.classList.toggle("selected",n.dataset.room===room.id));
}

function renderLedger() {
  const l=state.result.report.area_ledger_m2;
  const rows=[["program_usable","Programmed usable rooms","#a8c9de"],["circulation_clear","Clear circulation","#d5deeb"],["core_gross_reserve","Gross service reserve","#b7c3d2"],["walls","Physical walls","#7589a4"],["thresholds","Door / aperture thresholds","#e4c88d"]];
  return '<section class="card ledger-card"><div class="ledger-title">Area accounting <span>'+fmt(l.gross)+' m² gross</span></div><div class="ledger-bar">'+rows.map(([key,_name,color])=>'<span style="width:'+(100*l[key]/l.gross)+'%;background:'+color+'"></span>').join("")+'</div>'+rows.map(([key,name])=>'<div class="ledger-line"><span>'+name+'</span><strong>'+fmt(l[key])+' m²</strong></div>').join("")+'<div class="ledger-line" style="border-top:1px solid #e6ebf2;margin-top:9px;padding-top:12px"><span>Uncovered / overlapping</span><strong>'+fmt(l.uncovered)+' / '+fmt(l.duplicated)+' m²</strong></div></section>';
}

function renderReport(report) {
  const pass=report.checks.filter(c=>c.status==="pass").length, fail=report.checks.filter(c=>c.status==="fail").length, unverified=report.checks.filter(c=>c.status==="unverified").length;
  return '<section class="card report-card"><h2>Independent geometry report</h2><p class="intro">Recomputed from the exported polygons and the approved brief. Solver scores and declared door edges are not accepted as evidence.</p><div class="report-summary"><div class="passed-count"><strong>'+pass+'</strong>passed checks</div><div><strong>'+fail+'</strong>failed checks</div><div class="unverified-count"><strong>'+unverified+'</strong>unverified reviews</div></div><p class="report-note">'+esc(report.scope)+'<br>Validator '+esc(report.validator_version)+' · brief revision '+report.brief_revision+' · digest '+esc(report.brief_hash.slice(0,12))+'…</p>'+report.checks.map(c=>'<details class="check-item"><summary><span class="check-id">'+esc(c.id)+'</span><span class="check-title">'+esc(c.description)+'</span><span class="check-state '+c.status+'">'+(c.status==="unverified"?"UNVERIFIED":c.status.toUpperCase())+'</span></summary><div class="check-detail"><p><strong>Source:</strong> '+esc(c.source)+' · '+esc(c.provenance)+'</p><p><strong>Procedure:</strong> '+esc(c.validation_procedure)+'</p><p><strong>Scope:</strong> '+esc(c.scope)+' · '+esc(c.classification)+' · '+esc(c.implementation_status)+'</p><strong>Expected · '+esc(c.units)+'</strong><pre>'+esc(JSON.stringify(c.expected,null,2))+'</pre><strong>Measured · '+esc(c.units)+'</strong><pre>'+esc(JSON.stringify(c.measured,null,2))+'</pre><p><strong>Tolerance:</strong> '+esc(JSON.stringify(c.tolerance))+'</p>'+(c.geometry_ids.length?'<p><strong>Geometry:</strong> '+c.geometry_ids.map(esc).join(", ")+'</p>':"")+'</div></details>').join("")+'</section>'+reviewBanner();
}

function renderConflict(result) {
  const e=result.explanation||{};
  const title=result.search_status==="infeasible"?"The stated requirements conflict":result.search_status==="unsupported"?"This geometry needs a different layout model":result.search_status==="unknown"?"The search is unresolved":"A validated layout was not released";
  let stats="";
  if(e.required_m2!=null) stats='<div class="conflict-evidence"><div><strong>'+fmt(e.required_m2)+' m²</strong>Required room minimums</div><div><strong>'+fmt(e.available_m2)+' m²</strong>Entire inside shell</div><div><strong>'+fmt(e.deficit_m2)+' m²</strong>Minimum area deficit</div></div>';
  return '<section class="card status-card conflict"><div class="status-icon">'+(result.search_status==="unknown"?"?":"!")+'</div><h2>'+title+'</h2><p>'+esc(result.message)+'</p>'+stats+'<div class="conflict-details">'+(e.scope?'<p><strong>Evidence scope:</strong> '+esc(e.scope)+'</p>':"")+(e.requirement_ids?.length?'<p><strong>Requirements:</strong> '+e.requirement_ids.map(esc).join(", ")+'</p>':"")+(e.note?'<p>'+esc(e.note)+'</p>':"")+(e.suggestions||[]).map(s=>'<p>'+esc(s)+'</p>').join("")+'<p>'+ (result.search_status==="unknown"?"No conflict was established. Try another search or explicitly revise the brief.":result.search_status==="unsupported"?"Unsupported input is not a finding that an architectural solution is impossible.":"Mandatory requirements were retained. Review them explicitly before trying again.")+'</p></div><button class="button primary" data-action="edit-brief">Review and edit requirements →</button><p style="margin-top:18px;font-size:9px">Revision '+result.brief_revision+' · '+fmt(result.elapsed_seconds,3)+' seconds · no layout accepted</p></section>'+(result.report?renderReport(result.report):"");
}

function renderResult() {
  document.querySelectorAll("[data-result-tab]").forEach(n=>n.setAttribute("aria-selected",String(n.dataset.resultTab===state.tab)));
  const node=$("#resultBody");
  if(state.busy) return;
  const r=state.result;
  if(!r) {node.innerHTML=blankResult();setBusyButtons();return;}
  if(r.validation_status!=="passed" || !r.layout) {node.innerHTML=renderConflict(r);setBusyButtons();return;}
  $("#downloadJson").disabled=false;
  $("#downloadSvg").disabled=false;
  if(state.tab==="report") node.innerHTML=renderReport(r.report);
  else if(state.tab==="schedule") {
    const l=r.report.area_ledger_m2;
    node.innerHTML='<section class="card schedule-card"><h2>Measured room schedule</h2><p class="intro">Clear dimensions and areas are recomputed from exported room polygons. Walls, circulation and the service reserve are accounted for separately.</p><div class="table-scroll"><table class="data-table"><thead><tr><th>SPACE</th><th>CAPACITY</th><th class="numeric">CLEAR DIMENSIONS</th><th class="numeric">AREA m²</th><th class="numeric">MIN. m²</th><th class="numeric">MAX. m²</th></tr></thead><tbody>'+r.report.room_schedule.map(s=>'<tr><td>'+esc(s.name)+'</td><td>'+s.capacity+' '+(s.kind==="meeting"?"seats":"desk"+(s.capacity===1?"":"s"))+'</td><td class="numeric">'+fmt(s.width_mm/1000)+' × '+fmt(s.depth_mm/1000)+' m</td><td class="numeric">'+fmt(s.area_m2)+'</td><td class="numeric">'+fmt(s.minimum_m2)+'</td><td class="numeric">'+(s.maximum_m2==null?"—":fmt(s.maximum_m2))+'</td></tr>').join("")+'<tr><td colspan="3">Programmed usable rooms</td><td class="numeric">'+fmt(l.program_usable)+'</td><td colspan="2"></td></tr></tbody></table></div></section>'+reviewBanner();
  } else {
    const pass=r.report.checks.filter(c=>c.status==="pass"&&c.classification==="hard").length;
    node.innerHTML='<div class="result-grid"><section class="card plan-card"><div class="card-heading"><div><h2>Proposed office layout</h2><p>Clear room dimensions · select any room to inspect</p></div><span class="plan-tag">DIMENSIONED GEOMETRY</span></div><div class="plan-canvas" id="planCanvas"></div><div class="plan-legend">'+[["Reception",colors.reception],["Shared work",colors.workroom],["Private office",colors.office],["Meeting",colors.meeting],["Aperture","#e4c88d"]].map(([label,color])=>'<span><i style="background:'+color+'"></i>'+label+'</span>').join("")+'</div><div class="result-proof"><div class="proof-status"><i>✓</i>'+pass+' mandatory geometry checks passed</div><div class="proof-details">'+fmt(r.elapsed_seconds,3)+' s end to end · revision '+r.brief_revision+'<br>'+esc(r.layout.metadata.solver_status)+' in the encoded model</div></div></section><aside class="result-aside"><section class="card inspector" id="inspector"></section>'+renderLedger()+'</aside></div>'+reviewBanner();
    $("#planCanvas").innerHTML=r.svg;
    renderInspector();
  }
  setBusyButtons();
}

function setBusyButtons() {
  document.querySelectorAll('[data-action="generate"]').forEach(n=>n.disabled=state.busy||!state.brief);
  const ready=!!state.result && state.result.validation_status==="passed" && !!state.result.layout && !state.busy;
  $("#downloadJson").disabled=!ready; $("#downloadSvg").disabled=!ready;
}

function validateVisible() {
  const root=state.view==="brief"?$("#stepContent"):$("#quickMeeting");
  const inputs=root.tagName==="INPUT"?[root]:root.querySelectorAll("input,select");
  for(const n of inputs) if(!n.checkValidity()) {n.reportValidity();return false;}
  return true;
}

async function generate() {
  if(state.busy || !state.brief || !validateVisible()) return;
  showNotice("");
  const snapshot=clone(state.brief), revision=snapshot.revision;
  state.result=null;
  state.busy=true;
  setView("result");
  $("#resultBody").innerHTML='<section class="card status-card"><span class="spinner" aria-hidden="true"></span><h2>Finding a layout for your brief</h2><p>Searching the declared grid with your mandatory requirements intact. Any candidate must pass independent exported-geometry checks before it appears here.</p><div class="loading-time" role="status" aria-live="polite">Elapsed <span id="waitingSeconds">0</span> s · solver budget '+snapshot.solver.time_limit_seconds+' s</div></section>';
  setBusyButtons();
  let seconds=0;
  waitingTimer=setInterval(()=>{seconds++;if($("#waitingSeconds")) $("#waitingSeconds").textContent=seconds;},1000);
  const abort=new AbortController(), timeout=setTimeout(()=>abort.abort(),45000);
  try {
    const response=await fetch("/api/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(snapshot),signal:abort.signal});
    const result=await response.json();
    if(state.brief.revision!==revision) {
      showNotice("An earlier revision finished. Generate again to check the current brief.");
      return;
    }
    if(!response.ok) {
      fieldsError(result.detail?{message:result.detail}:result);
      state.step=2;
      setView("brief");
      return;
    }
    state.result=result;
    state.tab="plan";
  } catch(error) {
    showNotice(error.name==="AbortError"?"The request did not finish within the browser timeout. Its outcome is unresolved.":"The local application could not be reached. Check that run.py is running, then try again.",true);
  } finally {
    clearTimeout(timeout); clearInterval(waitingTimer);
    state.busy=false;
    if(state.view==="result") renderResult();
    updateSummary();setBusyButtons();
  }
}

async function loadPreset(name,initial=false) {
  try {
    const response=await fetch("/api/presets/"+encodeURIComponent(name),{cache:"no-store"});
    if(!response.ok) throw new Error("preset");
    const data=await response.json();
    data.revision=state.brief?state.brief.revision+1:1;
    state.brief=data; state.result=null;state.step=initial?0:2;state.fixedExpanded=false;state.dimensionMode="known";state.tab="plan";
    setView("brief");
    showNotice(initial?"":"Input loaded for review. Generate to solve this brief; no saved layout is used.");
  } catch(_error) {showNotice("The local application could not load the brief. Start run.py and reload this page.",true);}
}

function download(content,name,type) {
  const url=URL.createObjectURL(new Blob([content],{type}));
  const a=document.createElement("a");
  a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

async function exportSvg() {
  if(!state.result?.layout || state.result.validation_status!=="passed") return;
  const result=state.result, revision=state.brief.revision;
  try {
    const response=await fetch("/api/export/svg",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({brief:result.brief,layout:result.layout})});
    if(!response.ok) throw new Error("validation");
    const svg=await response.text();
    if(revision!==state.brief.revision) {showNotice("Export cancelled because the brief changed. Generate the current revision.");return;}
    download(svg,"office-floor-plan-r"+revision+".svg","image/svg+xml");
  } catch(_error) {showNotice("SVG export could not be validated. Generate again before downloading.",true);}
}

function handleControl(node) {
  const b=state.brief, key=node.dataset.control, value=node.value;
  if(key==="demoPreset") {if(value) loadPreset(value);return;}
  if(key==="dimensionMode") {state.dimensionMode=value;renderStep();return;}
  if(key==="officeCount") {
    const current=b.rooms.filter(r=>r.kind==="office"), desired=Number(value);
    if(desired<current.length) {
      const remove=current.slice(desired).map(r=>r.id);
      b.rooms=b.rooms.filter(r=>!remove.includes(r.id));
      b.relationships=b.relationships.filter(r=>!remove.includes(r.a)&&!remove.includes(r.b));
    } else {
      for(let i=current.length;i<desired;i++) b.rooms.splice(b.rooms.findIndex(r=>r.kind==="meeting"),0,{id:"office_"+String.fromCharCode(97+i),name:"Private office "+String.fromCharCode(65+i),kind:"office",capacity:1,min_area_m2:16,target_area_m2:19,max_area_m2:22});
    }
  } else if(key==="sharedCount"||key==="meetingCount") {
    b.rooms.find(r=>r.kind===(key==="sharedCount"?"workroom":"meeting")).capacity=Number(value);
  } else if(key==="obstructions") {
    b.fixed.other_obstructions=value==="yes"?[{x1:null,y1:null,x2:null,y2:null}]:[];
  } else if(key.startsWith("relationship")) {
    const kind=$('[data-control="relationshipKind"]').value;
    b.relationships=kind==="none"?[]:[{id:"room_link",a:$('[data-control="relationshipA"]').value,b:$('[data-control="relationshipB"]').value,kind,mandatory:kind!=="near"}];
    invalidate();
    const json=$("#briefJson");if(json) json.textContent=JSON.stringify(b,null,2);
    return;
  }
  invalidate();renderStep();
}

document.addEventListener("input",event=>{
  if(!state.brief) return;
  const node=event.target;
  if(node.id==="quickMeeting") {
    const value=node.value===""?null:Number(node.value);
    state.brief.rooms.find(r=>r.kind==="meeting").min_area_m2=value;
    invalidate("Requirements changed. The previous geometry report no longer validates this revision.");
    return;
  }
  if(!node.dataset.path || node.tagName==="SELECT") return;
  let value=node.value;
  if(node.type==="number") {
    value=value===""?null:Number(value);
    if(node.hasAttribute("data-mm")&&value!=null) {
      value*=1000;
      if(Math.abs(value-Math.round(value))<1e-7) value=Math.round(value);
    }
  }
  if(node.dataset.path==="location" && value==="") value=null;
  setPath(node.dataset.path,value);
  if(["floor.width_mm","floor.depth_mm"].includes(node.dataset.path)) state.fixedExpanded=true;
  invalidate();
});

document.addEventListener("change",event=>{
  if(!state.brief) return;
  const node=event.target;
  if(node.dataset.control) return handleControl(node);
  if(node.tagName==="SELECT" && node.dataset.path) {setPath(node.dataset.path,node.value);invalidate();}
});

document.addEventListener("click",async event=>{
  const node=event.target.closest("button,[data-room]");
  if(!node || !state.brief) return;
  if(node.dataset.preset) return loadPreset(node.dataset.preset);
  if(node.dataset.step!=null) {if(validateVisible()) {state.step=Number(node.dataset.step);renderStep();}return;}
  if(node.dataset.resultTab) {state.tab=node.dataset.resultTab;renderResult();return;}
  if(node.dataset.room) {state.selected=node.dataset.room;renderInspector();return;}
  if(node.dataset.removeOpening!=null) {
    state.brief.fixed.exterior_openings.splice(Number(node.dataset.removeOpening),1);
    invalidate();renderStep();return;
  }
  const action=node.dataset.action;
  if(action==="next") {if(validateVisible()) {state.step=Math.min(2,state.step+1);renderStep();showNotice("");}}
  else if(action==="back") {state.step=Math.max(0,state.step-1);renderStep();}
  else if(action==="view-brief"||action==="edit-brief") {if(action==="edit-brief") state.step=2;setView("brief");}
  else if(action==="view-result") setView("result");
  else if(action==="toggle-fixed") {state.fixedExpanded=!state.fixedExpanded;renderStep();}
  else if(action==="generate") await generate();
  else if(action==="download-svg") await exportSvg();
  else if(action==="download-json" && state.result?.validation_status==="passed") {
    const result=clone(state.result);delete result.svg;
    download(JSON.stringify(result,null,2),"office-floor-plan-r"+state.brief.revision+".json","application/json");
  } else if(action==="download-brief") download(JSON.stringify(state.brief,null,2),"office-brief-r"+state.brief.revision+".json","application/json");
  else if(action==="derive-boundary") {
    const area=Number($("#knownArea").value), ratio=Number($("#declaredRatio").value);
    if(!(area>0&&ratio>0)) {showNotice("Provide both the area and an explicit width/depth proportion.",true);return;}
    const grid=state.brief.rules.grid_mm;
    state.brief.floor.width_mm=Math.round(Math.sqrt(area*ratio)*1000/grid)*grid;
    state.brief.floor.depth_mm=Math.round(Math.sqrt(area/ratio)*1000/grid)*grid;
    state.brief.floor.source_status="assumed";
    state.brief.floor.source_note="Assumed rectangle adopted from "+area+" m² and a declared width/depth proportion of "+ratio+", rounded to "+grid+" mm. Fixed coordinates were retained.";
    state.dimensionMode="known";state.fixedExpanded=true;
    invalidate("Approximate boundary adopted as an assumption. Review the retained fixed coordinates explicitly.");
    renderStep();
  }
});

document.addEventListener("keydown",event=>{
  const room=event.target.closest("[data-room]");
  if(room && ["Enter"," "].includes(event.key)) {event.preventDefault();state.selected=room.dataset.room;renderInspector();}
});

loadPreset("baseline",true);
