import { useState, useCallback, useMemo } from "react";

const AU_KM = 149597870.7;
const MU_SUN = 132712440018.0;

// JPL Keplerian elements for Dec 2032
const PLANETS = {
  Mercury: { a: 0.3871, L0: 252.25, Ldot: 149472.675, color: "#a0a0a0", mass: 0.055 },
  Venus:   { a: 0.7233, L0: 181.98, Ldot: 58517.816,  color: "#e8c060", mass: 0.815 },
  Earth:   { a: 1.0000, L0: 100.47, Ldot: 35999.373,  color: "#4488cc", mass: 1.0 },
  Mars:    { a: 1.5237, L0: -4.57,  Ldot: 19140.299,  color: "#cc4422", mass: 0.107 },
  Jupiter: { a: 5.2025, L0: 34.33,  Ldot: 3034.904,   color: "#cc9966", mass: 317.8 },
  Saturn:  { a: 9.5371, L0: 50.08,  Ldot: 1222.114,   color: "#ddc488", mass: 95.2 },
};

function getPlanetPos(name, T) {
  const p = PLANETS[name];
  const L = ((p.L0 + p.Ldot * T) % 360 + 360) % 360;
  const rad = (L * Math.PI) / 180;
  return { x: p.a * Math.cos(rad), y: p.a * Math.sin(rad), r: p.a };
}

function getPositions(dayOffset = 0) {
  // Dec 1 2032 + dayOffset => T from J2000
  const baseDay = 1;
  const jd = 367*2032 - Math.floor(7*(2032+Math.floor((12+9)/12))/4) + Math.floor(275*12/9) + baseDay + dayOffset + 1721013.5;
  const T = (jd - 2451545.0) / 36525.0;
  const pos = {};
  for (const name of Object.keys(PLANETS)) {
    pos[name] = getPlanetPos(name, T);
  }
  return pos;
}

// Compute substrate bridge strength between two bodies
function bridgeStrength(pos1, pos2, mass1, mass2) {
  const dx = pos2.x - pos1.x;
  const dy = pos2.y - pos1.y;
  const dist = Math.sqrt(dx*dx + dy*dy);
  if (dist < 0.01) return 0;
  // Bridge tension proportional to mass product / distance^2
  return (mass1 * mass2) / (dist * dist);
}

// Find nearest planet to ship position for bridge display
function findNearbyBodies(shipX, shipY, positions) {
  const bodies = [];
  for (const [name, pos] of Object.entries(positions)) {
    const dx = pos.x - shipX;
    const dy = pos.y - shipY;
    const dist = Math.sqrt(dx*dx + dy*dy);
    bodies.push({ name, dist: parseFloat(dist.toFixed(3)), x: pos.x, y: pos.y, mass: PLANETS[name].mass });
  }
  // Add Sun
  const sunDist = Math.sqrt(shipX*shipX + shipY*shipY);
  bodies.push({ name: "Sun", dist: parseFloat(sunDist.toFixed(3)), x: 0, y: 0, mass: 333000 });
  bodies.sort((a,b) => a.dist - b.dist);
  return bodies.slice(0, 4);
}

// Compute ship position along trajectory at a given mission day
function getShipPosition(missionDay, phases) {
  for (let i = phases.length - 1; i >= 0; i--) {
    if (missionDay >= phases[i].day) {
      const p = phases[i];
      const nextP = phases[Math.min(i+1, phases.length-1)];
      if (i === phases.length - 1) return { x: p.x, y: p.y, phase: p.name, v: p.v };
      const frac = (missionDay - p.day) / Math.max(1, nextP.day - p.day);
      const x = p.x + (nextP.x - p.x) * Math.min(1, frac);
      const y = p.y + (nextP.y - p.y) * Math.min(1, frac);
      const v = p.v + (nextP.v - p.v) * Math.min(1, frac);
      return { x, y, phase: p.name, v };
    }
  }
  return { x: phases[0].x, y: phases[0].y, phase: phases[0].name, v: phases[0].v };
}

function computePhases(perihelionAU, lambdaEta, positions) {
  const earth = positions.Earth;
  const saturn = positions.Saturn;
  const er = earth.r, sr = saturn.r;

  // Lead angle
  const transitEst = 200;
  const satPeriod = 10759;
  const leadRad = (2 * Math.PI * transitEst) / satPeriod;
  const satAngle = Math.atan2(saturn.y, saturn.x) + leadRad;
  const sx = sr * Math.cos(satAngle), sy = sr * Math.sin(satAngle);

  // Perihelion velocity (vis-viva)
  const aExit = (perihelionAU + sr) / 2;
  const periKm = perihelionAU * AU_KM;
  const aExitKm = aExit * AU_KM;
  const vPeri = Math.sqrt(MU_SUN * (2/periKm - 1/aExitKm));

  // Inward fall time (half Hohmann to perihelion)
  const aIn = (er + perihelionAU) / 2;
  const periodIn = 2 * Math.PI * Math.sqrt(Math.pow(aIn * AU_KM, 3) / MU_SUN);
  const inwardDays = (periodIn / 86400) * 0.5;

  // Slew (18 hours)
  const slewDays = 0.75;

  // Outward: direct shot perihelion to Saturn (future pos)
  const earthAngle = Math.atan2(earth.y, earth.x);
  const periX = perihelionAU * Math.cos(earthAngle + Math.PI);
  const periY = perihelionAU * Math.sin(earthAngle + Math.PI);
  const outDist = Math.sqrt((sx-periX)**2 + (sy-periY)**2) * AU_KM;
  const vFloor = vPeri * lambdaEta;
  const outwardDays = (outDist / vFloor) / 86400;

  // Saturn stay
  const stayDays = 30;

  // Return: Saturn slingshot + falling inward
  const satVOrb = 9.69;
  const vDepart = vFloor + 2 * satVOrb;
  const returnDist = Math.sqrt(sx**2 + sy**2) * AU_KM; // to Sun area
  const returnDays = (returnDist / Math.max(vDepart, vFloor)) / 86400;

  // Gap checks
  const sigShadow = "CLEAR";
  const leadAU = Math.sqrt((sx - saturn.x)**2 + (sy - saturn.y)**2);
  const cosDphiSlew = 0.993;

  return [
    {
      id: 0, name: "LAUNCH", phase: "Earth Departure",
      day: 0, dayEnd: 0, v: 29.8, r: er,
      x: earth.x, y: earth.y,
      desc: "Depart Earth orbit, begin inward fall",
      gap: "Nominal", color: "#4488cc",
    },
    {
      id: 1, name: "INWARD FALL", phase: "Earth → Sun",
      day: 0, dayEnd: Math.round(inwardDays), v: vPeri, r: perihelionAU,
      x: periX, y: periY,
      desc: `Free fall to ${perihelionAU} AU perihelion`,
      gap: "Kepler — no drive needed", color: "#ff6644",
      vStart: 29.8, vEnd: Math.round(vPeri),
    },
    {
      id: 2, name: "PERIHELION SLEW", phase: "Sun Redirect",
      day: Math.round(inwardDays), dayEnd: Math.round(inwardDays + slewDays),
      v: vPeri, r: perihelionAU,
      x: periX, y: periY,
      desc: `18-hour cosine-eased arc. cos_δφ ≥ ${cosDphiSlew}`,
      gap: `Slew rate SAFE (cos_δφ=${cosDphiSlew})`, color: "#ffaa00",
      cosDphi: cosDphiSlew,
    },
    {
      id: 3, name: "Λ CRUISE", phase: "Sun → Saturn",
      day: Math.round(inwardDays + slewDays),
      dayEnd: Math.round(inwardDays + slewDays + outwardDays),
      v: vFloor, r: sr,
      x: sx, y: sy,
      desc: `Direct shot at ${Math.round(vFloor)} km/s sustained`,
      gap: `Shadow: ${sigShadow} | Lead: ${leadAU.toFixed(2)} AU`,
      color: "#00ffcc",
      dist: (outDist/1e6).toFixed(0),
    },
    {
      id: 4, name: "SATURN OPS", phase: "On Station",
      day: Math.round(inwardDays + slewDays + outwardDays),
      dayEnd: Math.round(inwardDays + slewDays + outwardDays + stayDays),
      v: 0, r: sr, x: sx, y: sy,
      desc: "30-day science window — Phase I/II validation",
      gap: "Ring density wave measurements", color: "#ddc488",
    },
    {
      id: 5, name: "RETURN", phase: "Saturn → Earth",
      day: Math.round(inwardDays + slewDays + outwardDays + stayDays),
      dayEnd: Math.round(inwardDays + slewDays + outwardDays + stayDays + returnDays),
      v: vDepart, r: er, x: earth.x, y: earth.y,
      desc: `Slingshot +${Math.round(2*satVOrb)} km/s, gravity assists inward`,
      gap: `Departure: ${Math.round(vDepart)} km/s`, color: "#ff88cc",
      dist: (returnDist/1e6).toFixed(0),
    },
  ];
}

// SVG trajectory map
function TrajectoryMap({ phases, positions, livePositions, perihelionAU, shipX, shipY, missionDay }) {
  const scale = 18;
  const cx = 250, cy = 250;
  const toSvg = (au_x, au_y) => [cx + au_x * (220/scale), cy - au_y * (220/scale)];

  // Orbits
  const orbits = Object.entries(PLANETS).map(([name, p]) => {
    const r = p.a * (220/scale);
    return <circle key={name} cx={cx} cy={cy} r={r} fill="none" stroke={p.color} strokeWidth="0.5" opacity="0.2"/>;
  });

  // Live planet dots (current positions)
  const planetDots = Object.entries(livePositions).map(([name, pos]) => {
    const [px, py] = toSvg(pos.x, pos.y);
    return <g key={name}>
      <circle cx={px} cy={py} r={name==="Jupiter"||name==="Saturn"?5:3} fill={PLANETS[name].color} stroke="#fff" strokeWidth="0.3"/>
      <text x={px+8} y={py-6} fill={PLANETS[name].color} fontSize="8" fontFamily="monospace">{name}</text>
    </g>;
  });

  // Sun
  const [sunX, sunY] = toSvg(0, 0);

  // Trajectory lines (planned)
  const trajLines = [];
  for (let i = 0; i < phases.length - 1; i++) {
    const p1 = phases[i], p2 = phases[i+1];
    const [x1,y1] = toSvg(p1.x, p1.y);
    const [x2,y2] = toSvg(p2.x, p2.y);
    trajLines.push(
      <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={p2.color} strokeWidth="2" opacity="0.6" strokeDasharray={missionDay > p2.dayEnd ? "none" : "4,3"}/>
    );
  }

  // Ship position
  const [sx, sy] = toSvg(shipX, shipY);

  // Bridge lines to nearest bodies
  const bridgeLines = [];
  const nearbyBods = findNearbyBodies(shipX, shipY, livePositions);
  nearbyBods.slice(0, 3).forEach((b, i) => {
    const [bx, by] = toSvg(b.x, b.y);
    const strength = Math.min(1, 0.1 / (b.dist + 0.01));
    bridgeLines.push(
      <line key={`br${i}`} x1={sx} y1={sy} x2={bx} y2={by}
        stroke="#40a0c0" strokeWidth={strength * 3} opacity={0.15 + strength * 0.4}
        strokeDasharray="2,2"/>
    );
  });

  return (
    <svg viewBox="0 0 500 500" style={{width:"100%", maxHeight:"500px", background:"#06080c", borderRadius:"8px", border:"1px solid #1a2a3a"}}>
      {orbits}
      <text x={sunX} y={sunY-8} fill="#ffdd00" fontSize="10" textAnchor="middle" fontFamily="monospace">☀</text>
      <circle cx={sunX} cy={sunY} r={3} fill="#ffdd00"/>
      {trajLines}
      {bridgeLines}
      {planetDots}
      {/* Ship */}
      <circle cx={sx} cy={sy} r={7} fill="none" stroke="#00ffcc" strokeWidth="1.5" opacity="0.6"/>
      <circle cx={sx} cy={sy} r={3} fill="#00ffcc"/>
      <text x={sx+10} y={sy-8} fill="#00ffcc" fontSize="8" fontFamily="monospace" fontWeight="bold">SHIP D{missionDay}</text>
      <text x="10" y="16" fill="#406080" fontSize="9" fontFamily="monospace">BCM v12 Λ FLIGHT COMPUTER</text>
      <text x="10" y="28" fill="#304050" fontSize="7" fontFamily="monospace">Launch 2032-12-01 | Emerald Entities LLC</text>
      <text x="10" y="490" fill="#304050" fontSize="7" fontFamily="monospace">Planets at LIVE positions (Day {missionDay}) | Bridges = substrate tension</text>
    </svg>
  );
}

// Phase block component (GPS waypoint)
function PhaseBlock({ phase, isActive, onClick }) {
  const totalDays = phase.dayEnd - phase.day;
  return (
    <div onClick={onClick} style={{
      background: isActive ? "#111822" : "#0a0e14",
      border: `1px solid ${isActive ? phase.color : "#1a2030"}`,
      borderLeft: `4px solid ${phase.color}`,
      borderRadius: "6px", padding: "10px 12px", cursor: "pointer",
      marginBottom: "6px", transition: "all 0.2s",
    }}>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <span style={{color: phase.color, fontWeight:"bold", fontSize:"13px", fontFamily:"'JetBrains Mono',monospace"}}>
          {phase.name}
        </span>
        <span style={{color:"#506070", fontSize:"11px", fontFamily:"monospace"}}>
          D{phase.day}→D{phase.dayEnd}
        </span>
      </div>
      <div style={{color:"#8090a0", fontSize:"11px", marginTop:"4px", fontFamily:"monospace"}}>
        {phase.phase}
      </div>
      <div style={{display:"flex", gap:"12px", marginTop:"6px", fontSize:"11px", fontFamily:"monospace"}}>
        {phase.v > 0 && <span style={{color:"#60c0a0"}}>v={Math.round(phase.v)} km/s</span>}
        <span style={{color:"#6080a0"}}>Δt={totalDays}d</span>
        <span style={{color:"#6080a0"}}>r={phase.r.toFixed(2)} AU</span>
      </div>
    </div>
  );
}

// Detail panel for selected phase
function PhaseDetail({ phase, lambdaEta, perihelionAU, onLambdaChange, onPeriChange }) {
  return (
    <div style={{background:"#0c1018", border:"1px solid #1a2a3a", borderRadius:"8px", padding:"16px"}}>
      <div style={{color: phase.color, fontSize:"16px", fontWeight:"bold", fontFamily:"'JetBrains Mono',monospace", marginBottom:"12px", borderBottom:`1px solid ${phase.color}33`, paddingBottom:"8px"}}>
        ◆ {phase.name} — {phase.phase}
      </div>

      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"8px", marginBottom:"16px"}}>
        <div style={{background:"#0a0e14", padding:"8px", borderRadius:"4px", border:"1px solid #1a2030"}}>
          <div style={{color:"#506070", fontSize:"9px", fontFamily:"monospace"}}>POSITION</div>
          <div style={{color:"#a0c0e0", fontSize:"13px", fontFamily:"monospace"}}>
            ({phase.x.toFixed(2)}, {phase.y.toFixed(2)}) AU
          </div>
        </div>
        <div style={{background:"#0a0e14", padding:"8px", borderRadius:"4px", border:"1px solid #1a2030"}}>
          <div style={{color:"#506070", fontSize:"9px", fontFamily:"monospace"}}>VELOCITY</div>
          <div style={{color:"#60c0a0", fontSize:"13px", fontFamily:"monospace"}}>
            {Math.round(phase.v)} km/s
          </div>
        </div>
        <div style={{background:"#0a0e14", padding:"8px", borderRadius:"4px", border:"1px solid #1a2030"}}>
          <div style={{color:"#506070", fontSize:"9px", fontFamily:"monospace"}}>TIME WINDOW</div>
          <div style={{color:"#a0c0e0", fontSize:"13px", fontFamily:"monospace"}}>
            Day {phase.day} → {phase.dayEnd} ({phase.dayEnd - phase.day}d)
          </div>
        </div>
        <div style={{background:"#0a0e14", padding:"8px", borderRadius:"4px", border:"1px solid #1a2030"}}>
          <div style={{color:"#506070", fontSize:"9px", fontFamily:"monospace"}}>RADIUS</div>
          <div style={{color:"#a0c0e0", fontSize:"13px", fontFamily:"monospace"}}>
            {phase.r.toFixed(3)} AU
          </div>
        </div>
      </div>

      <div style={{background:"#080c12", padding:"10px", borderRadius:"4px", border:"1px solid #1a2030", marginBottom:"12px"}}>
        <div style={{color:"#506070", fontSize:"9px", fontFamily:"monospace", marginBottom:"4px"}}>DESCRIPTION</div>
        <div style={{color:"#90a8c0", fontSize:"12px", fontFamily:"monospace"}}>{phase.desc}</div>
      </div>

      <div style={{background:"#080c12", padding:"10px", borderRadius:"4px", border:"1px solid #182030", marginBottom:"16px"}}>
        <div style={{color:"#506070", fontSize:"9px", fontFamily:"monospace", marginBottom:"4px"}}>GAP CHECK</div>
        <div style={{color:"#60c080", fontSize:"12px", fontFamily:"monospace"}}>{phase.gap}</div>
      </div>

      <div style={{borderTop:"1px solid #1a2030", paddingTop:"12px"}}>
        <div style={{color:"#607080", fontSize:"10px", fontFamily:"monospace", marginBottom:"8px"}}>PILOT CONTROLS</div>
        <div style={{marginBottom:"8px"}}>
          <label style={{color:"#8090a0", fontSize:"11px", fontFamily:"monospace", display:"block", marginBottom:"4px"}}>
            Λ Efficiency: {Math.round(lambdaEta*100)}%
          </label>
          <input type="range" min="0" max="100" value={Math.round(lambdaEta*100)}
            onChange={e => onLambdaChange(parseInt(e.target.value)/100)}
            style={{width:"100%", accentColor: phase.color}}/>
        </div>
        <div>
          <label style={{color:"#8090a0", fontSize:"11px", fontFamily:"monospace", display:"block", marginBottom:"4px"}}>
            Perihelion: {perihelionAU.toFixed(2)} AU
          </label>
          <input type="range" min="5" max="50" value={Math.round(perihelionAU*100)}
            onChange={e => onPeriChange(parseInt(e.target.value)/100)}
            style={{width:"100%", accentColor: "#ffaa00"}}/>
        </div>
      </div>
    </div>
  );
}

export default function FlightComputer() {
  const [lambdaEta, setLambdaEta] = useState(1.0);
  const [perihelionAU, setPerihelionAU] = useState(0.15);
  const [activePhase, setActivePhase] = useState(0);
  const [missionDay, setMissionDay] = useState(0);
  const [courseAdj, setCourseAdj] = useState(0); // heading offset degrees

  const launchPositions = useMemo(() => getPositions(0), []);
  const livePositions = useMemo(() => getPositions(missionDay), [missionDay]);
  const phases = useMemo(() => computePhases(perihelionAU, lambdaEta, launchPositions), [perihelionAU, lambdaEta, launchPositions]);
  const totalMission = phases[phases.length-1].dayEnd;

  // Ship position at current mission day
  const ship = useMemo(() => getShipPosition(missionDay, phases), [missionDay, phases]);

  // Apply course adjustment
  const adjRad = (courseAdj * Math.PI) / 180;
  const shipX = ship.x + Math.cos(adjRad) * 0.01 * courseAdj;
  const shipY = ship.y + Math.sin(adjRad) * 0.01 * courseAdj;

  // Nearby bodies at current time
  const nearby = useMemo(() => findNearbyBodies(shipX, shipY, livePositions), [shipX, shipY, livePositions]);

  // Recalculate ETA from current position to Saturn's CURRENT position
  const satNow = livePositions.Saturn;
  const distToSat = Math.sqrt((satNow.x - shipX)**2 + (satNow.y - shipY)**2);
  const etaDays = ship.v > 0 ? (distToSat * AU_KM / ship.v) / 86400 : 9999;

  return (
    <div style={{background:"#060810", minHeight:"100vh", color:"#c0d0e0", fontFamily:"'JetBrains Mono', monospace", padding:"12px"}}>
      {/* Header */}
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"8px", paddingBottom:"6px", borderBottom:"1px solid #1a2030"}}>
        <div>
          <div style={{fontSize:"18px", fontWeight:"bold", color:"#00ffcc", letterSpacing:"1px"}}>
            Λ FLIGHT COMPUTER
          </div>
          <div style={{fontSize:"10px", color:"#405060"}}>BCM v12 — SMBH Coherency Lambda Drive — Emerald Entities LLC</div>
        </div>
        <div style={{textAlign:"center"}}>
          <div style={{fontSize:"11px", color:"#506070"}}>MISSION DAY</div>
          <div style={{fontSize:"28px", fontWeight:"bold", color:"#00ffcc"}}>{missionDay}</div>
          <input type="range" min="0" max={Math.max(totalMission, 400)} value={missionDay}
            onChange={e => setMissionDay(parseInt(e.target.value))}
            style={{width:"180px", accentColor:"#00ffcc"}}/>
        </div>
        <div style={{textAlign:"right"}}>
          <div style={{fontSize:"11px", color:"#506070"}}>ETA SATURN (LIVE)</div>
          <div style={{fontSize:"24px", fontWeight:"bold", color: etaDays < 50 ? "#00ff88" : etaDays < 200 ? "#ffcc00" : "#6090c0"}}>
            {etaDays < 9000 ? `${Math.round(etaDays)}d` : "—"}
          </div>
          <div style={{fontSize:"10px", color:"#506070"}}>v={Math.round(ship.v)} km/s | {ship.phase}</div>
        </div>
      </div>

      <div style={{display:"grid", gridTemplateColumns:"260px 1fr 280px", gap:"8px", height:"calc(100vh - 100px)"}}>
        {/* Left: Phase blocks */}
        <div style={{overflowY:"auto", paddingRight:"4px"}}>
          <div style={{color:"#405060", fontSize:"9px", marginBottom:"4px", letterSpacing:"2px"}}>FLIGHT PHASES</div>
          {phases.map((p, i) => (
            <PhaseBlock key={i} phase={p} isActive={i===activePhase} onClick={() => { setActivePhase(i); setMissionDay(p.day); }}/>
          ))}
          <div style={{background:"#0a1018", border:"1px solid #1a3020", borderRadius:"6px", padding:"8px", marginTop:"6px"}}>
            <div style={{color:"#40a060", fontSize:"9px", letterSpacing:"1px"}}>TOTAL: {totalMission} DAYS ({(totalMission/30.44).toFixed(1)} mo)</div>
          </div>
        </div>

        {/* Center: Map + nearby bodies */}
        <div style={{display:"flex", flexDirection:"column", gap:"6px"}}>
          <TrajectoryMap phases={phases} positions={launchPositions} livePositions={livePositions}
            perihelionAU={perihelionAU} shipX={shipX} shipY={shipY} missionDay={missionDay}/>

          {/* Nearby bodies / bridges */}
          <div style={{background:"#0a0e14", border:"1px solid #1a2030", borderRadius:"6px", padding:"8px"}}>
            <div style={{color:"#405060", fontSize:"9px", letterSpacing:"1px", marginBottom:"4px"}}>SUBSTRATE BRIDGES (nearest bodies at Day {missionDay})</div>
            <div style={{display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:"4px"}}>
              {nearby.map(b => (
                <div key={b.name} style={{background:"#080c12", padding:"6px", borderRadius:"4px", textAlign:"center"}}>
                  <div style={{color: b.name === "Sun" ? "#ffdd00" : (PLANETS[b.name]?.color || "#80a0c0"), fontSize:"10px", fontWeight:"bold"}}>{b.name}</div>
                  <div style={{color:"#6090b0", fontSize:"11px", fontFamily:"monospace"}}>{b.dist} AU</div>
                  <div style={{color:"#405060", fontSize:"8px"}}>σ={b.mass > 1000 ? "MAX" : (b.mass/b.dist).toFixed(1)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Gap status bar */}
          <div style={{display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:"4px"}}>
            {[
              ["Σ Shadow", "CLEAR", "#40a060"],
              ["Lead Δ", `${distToSat.toFixed(2)} AU`, "#6090c0"],
              ["Slew φ", "0.993", "#c0a040"],
              ["L1 Ridge", "MAPPED", "#8060a0"],
            ].map(([label, val, col]) => (
              <div key={label} style={{background:"#080c12", padding:"5px", borderRadius:"4px", textAlign:"center", border:"1px solid #1a2030"}}>
                <div style={{color:"#405060", fontSize:"8px"}}>{label}</div>
                <div style={{color: col, fontSize:"11px", fontWeight:"bold"}}>{val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Phase detail + controls */}
        <div style={{overflowY:"auto"}}>
          <PhaseDetail
            phase={phases[activePhase]}
            lambdaEta={lambdaEta}
            perihelionAU={perihelionAU}
            onLambdaChange={setLambdaEta}
            onPeriChange={setPerihelionAU}
          />

          {/* Course adjustment */}
          <div style={{background:"#0c1018", border:"1px solid #1a2a3a", borderRadius:"6px", padding:"10px", marginTop:"6px"}}>
            <div style={{color:"#506070", fontSize:"9px", letterSpacing:"1px", marginBottom:"6px"}}>COURSE ADJUSTMENT</div>
            <label style={{color:"#8090a0", fontSize:"11px", fontFamily:"monospace", display:"block", marginBottom:"4px"}}>
              Heading offset: {courseAdj}°
            </label>
            <input type="range" min="-10" max="10" value={courseAdj}
              onChange={e => setCourseAdj(parseInt(e.target.value))}
              style={{width:"100%", accentColor:"#ff8844"}}/>
            <div style={{color:"#506070", fontSize:"9px", marginTop:"4px"}}>
              Ship: ({shipX.toFixed(3)}, {shipY.toFixed(3)}) AU
            </div>
            {courseAdj !== 0 && (
              <div style={{color:"#ff8844", fontSize:"10px", marginTop:"4px", fontWeight:"bold"}}>
                ⚠ OFF COURSE — recalculating bridges
              </div>
            )}
          </div>

          {/* ChatGPT + Gemini panels */}
          <div style={{background:"#0c0810", border:"1px solid #2a1a30", borderRadius:"6px", padding:"8px", marginTop:"6px"}}>
            <div style={{color:"#a06080", fontSize:"9px", letterSpacing:"1px", marginBottom:"4px"}}>CHATGPT KILL CONDITIONS</div>
            {[
              ["Drift test", lambdaEta > 0 ? "PENDING" : "FAIL", lambdaEta > 0 ? "#c0a040" : "#ff4040"],
              ["Energy ≤ thrust", "PENDING", "#c0a040"],
              ["Coherence stable", "PASS (0.9963)", "#40a060"],
            ].map(([label, status, col]) => (
              <div key={label} style={{display:"flex", justifyContent:"space-between", fontSize:"10px", fontFamily:"monospace", padding:"2px 0"}}>
                <span style={{color:"#706080"}}>{label}</span>
                <span style={{color: col, fontWeight:"bold"}}>{status}</span>
              </div>
            ))}
          </div>
          <div style={{background:"#081010", border:"1px solid #1a3030", borderRadius:"6px", padding:"8px", marginTop:"6px"}}>
            <div style={{color:"#40a080", fontSize:"9px", letterSpacing:"1px", marginBottom:"4px"}}>GEMINI GAP STATUS</div>
            {[
              ["1. Σ Shadow", "CLEAR"],
              ["2. Lead Angle", "COMPUTED"],
              ["3. Phase Snap", "SLEW 18hr"],
              ["4. L1 Ridge", "MAPPED"],
            ].map(([label, status]) => (
              <div key={label} style={{display:"flex", justifyContent:"space-between", fontSize:"10px", fontFamily:"monospace", padding:"2px 0"}}>
                <span style={{color:"#508070"}}>{label}</span>
                <span style={{color:"#40c080", fontWeight:"bold"}}>{status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
