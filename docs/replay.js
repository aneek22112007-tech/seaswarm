// Simulated replay of the Sagar-4 scenario from scripts/replay_demo.py.
// Plan figures are the output of core/plans.py for the seeded room.
const S=[
["ramesh · community_leader","human","Sagar-4 overdue by 2 hours, not back. Last seen near the reef, 6 km out."],
["context","agent","Situation: Sagar-4, 3 crew, out of Harnai (Ratnagiri).\nLast radio fix 12:30 IST, 17.8136 N 73.0394 E, heading 250°.\nOverdue 2.0 h · daylight left 4.0 h · drift cone computed from wind, sea state and tide.\n@options"],
["options","agent","Three options for Sagar-4\nA · Meerabai → Sector-2 · 100% · 1.45 h · 4.1 L · INR 389.50 · margin 2.55 h\nB · Meerabai, Chandra-2 → Sector-2, Sector-1 · 1.65 h · 9.4 L · INR 893.00 · margin 2.35 h\nC · Meerabai, Chandra-2, Harnai-Queen → all sectors · 1.95 h · 16.7 L · INR 1586.50 · margin 2.05 h\nRisk flags: none at a 14:30 start (room marks rough seas after 16:30).\n@action"],
["action","agent","PENDING approval: Coast Guard / marine police escalation drafted.\nFamily matched against scheme rules (eligibility, documents, deadlines).\n📌 Operation checklist pinned. Follow-up prompts scheduled."],
["sunita · family_rep","human","Approved — escalation"],
["action","deny","⛔ Refused. Escalation belongs to the community leader."],
["ramesh · community_leader","human","Approved — escalation"],
["action","ok","✅ ramesh (community_leader) approved escalation. Approver, role, message id and time written to the audit."],
["sunita · family_rep","human","photo: https://example.test/reef.jpg"],
["action","agent","Evidence recorded against the operation."],
["ramesh · community_leader","human","/audit"],
["action","ok","📜 Audit exported: Markdown + PDF in .runtime/exports/ — operation, sectors, every sign-off, evidence, append-only event log."]];
const room=document.getElementById('room');let i=0,t=null;
function step(){if(i>=S.length){t=null;return}const[w,c,x]=S[i++];const d=document.createElement('div');d.className='msg '+(c==='human'?'human':c==='agent'?'agent':c);d.innerHTML='<b>'+w+'</b>';d.appendChild(document.createTextNode(x));room.appendChild(d);room.scrollTop=room.scrollHeight;t=setTimeout(step,1600)}
document.getElementById('play').onclick=()=>{if(!t)step()};
document.getElementById('reset').onclick=()=>{clearTimeout(t);t=null;i=0;room.innerHTML=''};
const io=new IntersectionObserver(es=>es.forEach(e=>e.isIntersecting&&e.target.classList.add('in')),{threshold:.2});
document.querySelectorAll('.card').forEach(c=>io.observe(c));
