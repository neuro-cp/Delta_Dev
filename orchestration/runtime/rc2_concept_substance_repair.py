"""RC2.5A concept substance repair for synthesis trial inputs.

This module enriches existing approved noncanonical concepts in place while
preserving concept IDs, rollback handles, and canonical/training safety
boundaries. It does not create new concepts, train models, call providers,
or enable synthesis.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_developmental_concept_memory import KNOWLEDGE_MEMORY_LOG
from orchestration.runtime.rc2_synthesis_trial_report import build_synthesis_trial_report, score_concept_substance


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "synthesis_enabled_by_default": False,
}


SUBSTANCE_REPAIRS: dict[str, dict[str, Any]] = {
    "Cellular Respiration (Biology)": {
        "definition": "Cellular respiration is the process cells use to release usable energy from sugars by converting glucose and oxygen into carbon dioxide, water, and ATP.",
        "propositions": [
            "Cellular respiration converts stored chemical energy into ATP.",
            "Cellular respiration commonly uses glucose and oxygen as inputs.",
            "Cellular respiration produces carbon dioxide, water, and usable cellular energy.",
        ],
        "examples": ["Muscle cells using glucose and oxygen to produce ATP during activity."],
        "misconceptions": ["Cellular respiration is not the same process as breathing, although breathing supplies oxygen and removes carbon dioxide."],
        "related": ["ATP", "glucose", "oxygen", "carbon dioxide", "photosynthesis", "energy transformation"],
    },
    "Photosynthesis (Agriculture Gardening)": {
        "definition": "Photosynthesis in plants converts sunlight, carbon dioxide, and water into sugars that support plant growth while releasing oxygen.",
        "propositions": [
            "Photosynthesis stores light energy in chemical bonds.",
            "Plant growth depends on photosynthesis producing sugars.",
            "Photosynthesis links sunlight, water, carbon dioxide, and plant biomass.",
        ],
        "examples": ["A tomato plant using sunlight to produce sugars that support leaves, roots, flowers, and fruit."],
        "misconceptions": ["Fertilizer does not replace photosynthesis; nutrients support growth but do not provide the plant's main energy source."],
        "related": ["chlorophyll", "plant growth", "carbon dioxide", "water", "sugars", "cellular respiration"],
    },
    "Photosynthesis (Biology)": {
        "definition": "Photosynthesis is the biological pathway that captures light energy and stores it as chemical energy, usually in sugars made from carbon dioxide and water.",
        "propositions": [
            "Photosynthesis captures light energy.",
            "Photosynthesis stores energy in sugar molecules.",
            "Photosynthesis supplies energy-rich molecules that respiration can later break down.",
        ],
        "examples": ["Leaf cells using chloroplasts to make glucose from carbon dioxide and water."],
        "misconceptions": ["Photosynthesis is not simply plant breathing; it is an energy-storage pathway."],
        "related": ["chloroplasts", "glucose", "carbon cycle", "cellular respiration", "oxygen", "energy storage"],
    },
    "Energy Storage (Energy)": {
        "definition": "Energy storage preserves energy in a form that can be released later, such as chemical bonds, batteries, heat reservoirs, or elevated water.",
        "propositions": [
            "Energy storage separates energy capture from energy use.",
            "Stored energy can be chemical, thermal, mechanical, or electrical.",
            "Energy storage introduces tradeoffs in capacity, efficiency, speed, and stability.",
        ],
        "examples": ["A battery storing electrical energy chemically for later discharge."],
        "misconceptions": ["Energy storage does not create energy; it changes when and how energy can be used."],
        "related": ["battery chemistry", "chemical bonds", "thermal storage", "ATP", "grid storage"],
    },
    "Thermal Storage (Energy)": {
        "definition": "Thermal storage holds energy as heat or cold so it can be released later for heating, cooling, industrial processes, or power systems.",
        "propositions": [
            "Thermal storage stores energy through temperature differences or phase changes.",
            "Thermal storage can shift energy use from one time period to another.",
            "Thermal storage performance depends on insulation, heat capacity, and loss rate.",
        ],
        "examples": ["Molten salt storing heat from solar thermal systems for electricity generation after sunset."],
        "misconceptions": ["Thermal storage is not always electricity storage; it may store heat directly."],
        "related": ["heat capacity", "phase change", "insulation", "solar thermal energy", "energy storage"],
    },
    "Interest Rates (Finance)": {
        "definition": "Interest rates are the cost of borrowing money or the return for lending it, usually expressed as a percentage over time.",
        "propositions": [
            "Higher interest rates make borrowing more expensive.",
            "Interest rates influence saving, investment, asset prices, and debt payments.",
            "Central banks may adjust interest rates in response to inflation and economic conditions.",
        ],
        "examples": ["A mortgage payment rising when the loan interest rate increases."],
        "misconceptions": ["An interest rate is not the same thing as inflation, though the two often influence each other."],
        "related": ["inflation", "borrowing", "central banks", "compound interest", "monetary policy"],
    },
    "Inflation (Finance)": {
        "definition": "Inflation is a sustained rise in the general price level, reducing the purchasing power of money over time.",
        "propositions": [
            "Inflation means the same amount of money buys fewer goods or services.",
            "Inflation can be influenced by demand, supply shocks, money supply, and expectations.",
            "Inflation often affects interest-rate decisions and wage negotiations.",
        ],
        "examples": ["A grocery basket costing more this year than last year for similar items."],
        "misconceptions": ["Inflation is not any single price increase; it refers to broad price-level movement."],
        "related": ["purchasing power", "interest rates", "monetary policy", "consumer prices", "wages"],
    },
    "Asset Allocation (Finance)": {
        "definition": "Asset allocation is the way an investor divides money among categories such as stocks, bonds, cash, real estate, or other assets.",
        "propositions": [
            "Asset allocation shapes risk and expected return.",
            "Diversification across assets can reduce exposure to any single category.",
            "Asset allocation choices depend on time horizon, liquidity needs, and risk tolerance.",
        ],
        "examples": ["A retirement portfolio split between stock funds, bond funds, and cash reserves."],
        "misconceptions": ["Asset allocation is not a guarantee against loss; it manages exposure and tradeoffs."],
        "related": ["diversification", "risk tolerance", "portfolio", "bonds", "stocks", "inflation"],
    },
    "Balance Sheets (Finance)": {
        "definition": "A balance sheet is a financial statement that summarizes assets, liabilities, and equity at a specific point in time.",
        "propositions": [
            "Assets represent resources owned or controlled.",
            "Liabilities represent obligations owed.",
            "Equity is the residual interest after liabilities are subtracted from assets.",
        ],
        "examples": ["A company listing cash, inventory, debt, and shareholder equity at quarter end."],
        "misconceptions": ["A balance sheet is not the same as an income statement; it shows position, not period profit."],
        "related": ["assets", "liabilities", "equity", "financial statements", "cash flow"],
    },
    "Compound Interest (Finance)": {
        "definition": "Compound interest is interest calculated on both the original principal and previously accumulated interest.",
        "propositions": [
            "Compounding causes balances to grow faster over time than simple interest.",
            "The effect of compound interest depends on rate, time, and compounding frequency.",
            "Compound interest can benefit savers and increase costs for borrowers.",
        ],
        "examples": ["Savings growing as each year's interest also earns interest in later years."],
        "misconceptions": ["Compound interest is not linear growth; its effect accelerates over longer periods."],
        "related": ["interest rates", "principal", "time horizon", "debt", "investment returns"],
    },
    "Canonical Memory (Delta Architecture Itself)": {
        "definition": "Canonical memory is DELTA's governed long-term memory layer for records that have passed stricter review, provenance, rollback, and promotion requirements.",
        "propositions": [
            "Canonical memory requires stronger approval than noncanonical memory.",
            "Canonical memory should preserve provenance and rollback handles.",
            "Canonical memory remains disabled unless explicit gates allow it.",
        ],
        "examples": ["A repeatedly verified project fact promoted after review, contradiction checks, and rollback planning."],
        "misconceptions": ["Canonical memory is not casual chat memory and should not be written automatically."],
        "related": ["noncanonical memory", "provenance", "rollback", "operator approval", "promotion policy"],
    },
    "Noncanonical Memory (Delta Architecture Itself)": {
        "definition": "Noncanonical memory is DELTA's reversible, operator-reviewed substrate for tentative or useful knowledge that has not become canonical.",
        "propositions": [
            "Noncanonical memory can support retrieval without becoming permanent truth.",
            "Noncanonical memory remains reversible and reviewable.",
            "Noncanonical memory is the preferred early learning substrate before canonical promotion.",
        ],
        "examples": ["A user-approved concept stored for later testing while canonical writes remain off."],
        "misconceptions": ["Noncanonical memory is not model training and does not change neural weights."],
        "related": ["canonical memory", "concept review", "rollback", "developmental learning", "operator approval"],
    },
    "Memory Consolidation (Psychology)": {
        "definition": "Memory consolidation is the process by which fragile new memories become more stable and integrated over time.",
        "propositions": [
            "Consolidation helps transform short-term traces into more durable memory.",
            "Sleep and repeated retrieval can influence consolidation.",
            "Consolidation can integrate new information with prior knowledge.",
        ],
        "examples": ["Remembering a practiced skill better after rest and repeated use."],
        "misconceptions": ["Consolidation is not perfect copying; memories can be reconstructed and changed."],
        "related": ["learning", "sleep", "retrieval practice", "long-term memory", "forgetting"],
    },
    "Active Listening (Psychology)": {
        "definition": "Active listening is a communication practice where a listener attends carefully, reflects meaning, and checks understanding before responding.",
        "propositions": [
            "Active listening improves mutual understanding.",
            "Active listening often uses paraphrasing, clarification, and validation.",
            "Active listening can reduce conflict by separating interpretation from assumption.",
        ],
        "examples": ["Repeating a speaker's concern in your own words before offering advice."],
        "misconceptions": ["Active listening is not passive agreement; it is careful understanding and feedback."],
        "related": ["communication", "empathy", "clarification", "feedback loops", "conflict reduction"],
    },
    "Attachment (Psychology)": {
        "definition": "Attachment describes enduring emotional bonds that influence how people seek safety, support, and connection in relationships.",
        "propositions": [
            "Attachment patterns can affect trust, closeness, and responses to stress.",
            "Early caregiver relationships can influence later attachment patterns.",
            "Attachment is adaptive but can vary across contexts and relationships.",
        ],
        "examples": ["A child seeking comfort from a caregiver when frightened."],
        "misconceptions": ["Attachment style is not a fixed destiny; relationships and experience can change patterns."],
        "related": ["relationships", "development", "emotion regulation", "security", "trust"],
    },
    "Feedback Loops (Planning Productivity)": {
        "definition": "Feedback loops in planning are cycles where outcomes are compared with goals so plans can be adjusted.",
        "propositions": [
            "Feedback loops reveal whether a plan is working.",
            "Feedback loops support course correction before failure becomes expensive.",
            "Feedback quality depends on timely, relevant, and interpretable signals.",
        ],
        "examples": ["A weekly project review comparing actual progress against planned milestones."],
        "misconceptions": ["A feedback loop is not just criticism; it is information used to adjust behavior or plans."],
        "related": ["planning", "iteration", "metrics", "course correction", "software architecture"],
    },
    "Feedback Loops (Biology)": {
        "definition": "Biological feedback loops are regulatory cycles where a system's output influences future activity to maintain stability or amplify change.",
        "propositions": [
            "Negative feedback helps maintain homeostasis.",
            "Positive feedback amplifies a process until a stopping condition occurs.",
            "Feedback loops connect sensing, response, and regulation.",
        ],
        "examples": ["Body temperature regulation using sweating or shivering."],
        "misconceptions": ["Positive feedback is not always good; it means amplifying change."],
        "related": ["homeostasis", "regulation", "signals", "control systems", "planning feedback"],
    },
    "Access Control (Software Architecture)": {
        "definition": "Access control is the software architecture practice of deciding who or what may read, change, execute, or administer a resource.",
        "propositions": [
            "Access control protects resources by enforcing permissions.",
            "Access control depends on identity, policy, and authorization checks.",
            "Weak access control can allow unauthorized data exposure or actions.",
        ],
        "examples": ["A web app allowing admins to manage users while ordinary users can only view their own records."],
        "misconceptions": ["Authentication is not the same as authorization; login identifies a user, access control decides permissions."],
        "related": ["authorization", "authentication", "least privilege", "security", "software architecture"],
    },
    "Adapter Pattern (Software Architecture)": {
        "definition": "The adapter pattern lets incompatible interfaces work together by wrapping one interface with another expected shape.",
        "propositions": [
            "Adapters translate between existing code and expected interfaces.",
            "Adapters can reduce coupling when integrating external or legacy systems.",
            "Adapters should clarify boundaries rather than hide incompatible behavior.",
        ],
        "examples": ["Wrapping a payment provider API so the application calls a consistent internal payment interface."],
        "misconceptions": ["An adapter is not a full rewrite; it is a compatibility layer."],
        "related": ["interfaces", "integration", "wrappers", "decoupling", "software architecture"],
    },
    "Attention Budgeting (Planning Productivity)": {
        "definition": "Attention budgeting is the practice of allocating limited focus to the tasks, decisions, or signals that matter most.",
        "propositions": [
            "Attention is limited and must be prioritized.",
            "Attention budgeting reduces distraction and decision fatigue.",
            "Attention budgets should match task importance, urgency, and cognitive load.",
        ],
        "examples": ["Blocking the first hour of the day for high-priority design work before checking messages."],
        "misconceptions": ["Attention budgeting is not simply doing more; it is choosing what deserves focus."],
        "related": ["prioritization", "planning", "focus", "cognitive load", "feedback loops"],
    },
    "Break Even Analysis (Finance)": {
        "definition": "Break-even analysis identifies the sales volume or revenue level where total revenue equals total costs, so profit is zero before gains begin.",
        "propositions": [
            "Break-even analysis compares fixed costs, variable costs, price, and expected sales volume.",
            "A business is below break-even when revenue does not cover total costs.",
            "Break-even analysis helps evaluate pricing, cost control, and launch feasibility.",
        ],
        "examples": ["A shop calculating how many units it must sell each month to cover rent, labor, materials, and other costs."],
        "misconceptions": ["Break-even does not mean a project is attractive; it only marks the point where losses stop and profit can begin."],
        "related": ["fixed costs", "variable costs", "pricing", "profit margin", "budget variance"],
    },
    "Budget Variance (Finance)": {
        "definition": "Budget variance is the difference between planned financial amounts and actual results, used to identify overruns, savings, or planning errors.",
        "propositions": [
            "Budget variance can be favorable or unfavorable depending on whether results improve or worsen the plan.",
            "Variance analysis helps explain why actual spending or revenue differed from expectations.",
            "Persistent budget variance can reveal forecasting problems, cost changes, or execution issues.",
        ],
        "examples": ["A department budgeted $10,000 for software but spent $12,000, creating a $2,000 unfavorable expense variance."],
        "misconceptions": ["A variance is not automatically bad; favorable revenue or cost variance can indicate better-than-planned performance."],
        "related": ["forecasting", "actuals", "expense control", "break-even analysis", "financial planning"],
    },
    "Attention (Psychology)": {
        "definition": "Attention is the cognitive process of selecting some information for focused processing while filtering or deprioritizing other information.",
        "propositions": [
            "Attention is limited and can be directed by goals, novelty, emotion, or external cues.",
            "Attention affects perception, memory encoding, decision-making, and task performance.",
            "Divided attention often reduces accuracy or depth of processing compared with focused attention.",
        ],
        "examples": ["Focusing on a speaker's voice in a noisy room while ignoring background conversations."],
        "misconceptions": ["Attention is not unlimited awareness; it is selective and can miss important information outside the current focus."],
        "related": ["working memory", "focus", "distraction", "attention switching", "cognitive load"],
    },
    "Attention Switching (Psychology)": {
        "definition": "Attention switching is the act of shifting focus from one task, stimulus, or mental frame to another, often with a cognitive cost.",
        "propositions": [
            "Attention switching can reduce efficiency because the mind must reorient to a new context.",
            "Frequent switching can increase errors, fatigue, and lost time.",
            "Attention switching is useful when priorities change or new information becomes more important.",
        ],
        "examples": ["Stopping code review to answer a message, then needing time to recover the original reasoning context."],
        "misconceptions": ["Rapid switching is not the same as true parallel thinking; most demanding tasks compete for the same limited attention."],
        "related": ["attention", "task switching", "cognitive load", "focus", "attention budgeting"],
    },
    "Api Boundaries (Software Architecture)": {
        "definition": "API boundaries define the contracts, responsibilities, and allowed interactions between software components or services.",
        "propositions": [
            "API boundaries reduce coupling by hiding internal implementation details behind stable interfaces.",
            "Clear API boundaries make ownership, validation, and error handling easier to reason about.",
            "Weak API boundaries can spread assumptions across systems and make changes risky.",
        ],
        "examples": ["A runtime module exposing a small function for answer routing while keeping its internal scoring rules private."],
        "misconceptions": ["An API boundary is not just a URL or function name; it is the behavioral contract between caller and provider."],
        "related": ["interfaces", "contracts", "encapsulation", "adapter pattern", "access control"],
    },
    "Backlog Grooming (Planning Productivity)": {
        "definition": "Backlog grooming is the recurring practice of reviewing, clarifying, prioritizing, and sizing pending work before execution.",
        "propositions": [
            "Backlog grooming keeps future work understandable, ordered, and ready for planning.",
            "Good grooming removes stale tasks, splits oversized work, and clarifies acceptance criteria.",
            "Backlog grooming supports better sprint planning by reducing ambiguity before commitment.",
        ],
        "examples": ["A team reviewing pending feature tickets, adding missing requirements, and moving low-value items lower in priority."],
        "misconceptions": ["Backlog grooming is not the same as doing the work; it prepares work so execution is less confused."],
        "related": ["prioritization", "planning", "acceptance criteria", "feedback loops", "project management"],
    },
    "Budgeting (Finance)": {
        "definition": "Budgeting is the process of planning expected income, expenses, savings, and constraints so resources can be allocated deliberately.",
        "propositions": [
            "Budgeting converts financial goals and limits into a usable spending plan.",
            "A budget can be compared with actual results to identify variance.",
            "Budgeting supports tradeoff decisions when resources are limited.",
        ],
        "examples": ["A household assigning monthly income to rent, food, savings, debt payments, and discretionary spending."],
        "misconceptions": ["Budgeting is not only restriction; it is a planning tool for deciding what money should do."],
        "related": ["budget variance", "cash flow", "financial planning", "expense control", "forecasting"],
    },
    "Capital Budgeting (Finance)": {
        "definition": "Capital budgeting evaluates long-term investments by comparing expected costs, benefits, risks, timing, and strategic fit.",
        "propositions": [
            "Capital budgeting supports decisions about major projects or assets.",
            "Capital budgeting often considers cash flows, payback period, net present value, and risk.",
            "Capital budgeting differs from operating budgets because it focuses on long-lived investments.",
        ],
        "examples": ["A company evaluating whether a new manufacturing machine is worth its upfront cost and future maintenance."],
        "misconceptions": ["Capital budgeting is not just buying equipment; it is evaluating whether long-term investment creates enough value."],
        "related": ["investment analysis", "cash flow", "net present value", "break-even analysis", "risk assessment"],
    },
    "Audit Logs (Software Architecture)": {
        "definition": "Audit logs are structured records of important system events used to trace actions, diagnose behavior, and support accountability.",
        "propositions": [
            "Audit logs record who or what performed an action, when it happened, and what changed.",
            "Audit logs support debugging, compliance, rollback analysis, and incident investigation.",
            "Useful audit logs must be tamper-resistant enough to preserve trust in the recorded history.",
        ],
        "examples": ["A memory system recording that an operator approved a noncanonical concept at a specific time with a rollback handle."],
        "misconceptions": ["Audit logs are not the same as verbose debug logs; they preserve accountability for significant events."],
        "related": ["provenance", "rollback", "access control", "observability", "software architecture"],
    },
    "Calendar Planning (Planning Productivity)": {
        "definition": "Calendar planning assigns work, commitments, and recovery time to specific dates or time blocks so intentions become scheduled actions.",
        "propositions": [
            "Calendar planning turns priorities into time-bound commitments.",
            "Calendar planning helps reveal overload, conflicts, and unrealistic expectations.",
            "Calendar plans should adapt when feedback shows that estimates or priorities were wrong.",
        ],
        "examples": ["Blocking focused work in the morning, meetings in the afternoon, and review time at the end of the week."],
        "misconceptions": ["Calendar planning is not a guarantee that work will happen; it is a coordination tool that still needs feedback and adjustment."],
        "related": ["time blocking", "prioritization", "feedback loops", "attention budgeting", "project planning"],
    },
    "Cash Flow (Finance)": {
        "definition": "Cash flow is the movement of money into and out of an organization, project, or household over a period of time.",
        "propositions": [
            "Positive cash flow means more cash enters than leaves during the measured period.",
            "Cash flow can differ from profit because timing, credit, inventory, and capital spending affect cash availability.",
            "Cash flow analysis helps determine whether obligations can be paid when they come due.",
        ],
        "examples": ["A profitable company struggling because customers pay invoices slowly while payroll and rent are due now."],
        "misconceptions": ["Cash flow is not identical to revenue or profit; it focuses on actual cash timing."],
        "related": ["liquidity", "budgeting", "cash reserves", "working capital", "financial planning"],
    },
    "Cash Reserves (Finance)": {
        "definition": "Cash reserves are readily available funds kept to handle emergencies, volatility, delayed income, or planned near-term needs.",
        "propositions": [
            "Cash reserves improve resilience when revenue falls or expenses arrive unexpectedly.",
            "Cash reserves reduce liquidity risk but may earn lower returns than long-term investments.",
            "Appropriate reserve size depends on obligations, income stability, risk tolerance, and access to credit.",
        ],
        "examples": ["A small business keeping three months of operating expenses available in a liquid account."],
        "misconceptions": ["Cash reserves are not wasted money; they trade some return for flexibility and survival capacity."],
        "related": ["liquidity", "cash flow", "risk management", "emergency fund", "asset allocation"],
    },
    "Behavior Change (Psychology)": {
        "definition": "Behavior change is the process of altering habits or actions through motivation, cues, feedback, reinforcement, and environmental design.",
        "propositions": [
            "Behavior change is easier when desired actions are specific, cued, and reinforced.",
            "Environment and defaults can shape behavior even when motivation is limited.",
            "Sustained behavior change often requires feedback and adjustment over time.",
        ],
        "examples": ["Putting running shoes by the door to make morning exercise easier to start."],
        "misconceptions": ["Behavior change is not only willpower; context, incentives, habits, and feedback strongly influence outcomes."],
        "related": ["habits", "behavioral cues", "reinforcement", "feedback loops", "motivation"],
    },
    "Behavioral Cues (Psychology)": {
        "definition": "Behavioral cues are signals in a person or environment that prompt, shape, or trigger a behavior.",
        "propositions": [
            "Behavioral cues can be external, such as alarms or visual reminders, or internal, such as emotions or cravings.",
            "Changing cues can make desired behavior easier or unwanted behavior less automatic.",
            "Behavioral cues often work with rewards and routines to form habits.",
        ],
        "examples": ["A calendar reminder cueing someone to take medication at the same time each day."],
        "misconceptions": ["A cue does not force behavior; it increases the likelihood of a response in a context."],
        "related": ["habits", "behavior change", "attention", "environment design", "routine"],
    },
    "Caching (Software Architecture)": {
        "definition": "Caching stores previously computed or retrieved data in a faster-access layer so repeated requests can be served more efficiently.",
        "propositions": [
            "Caching can reduce latency, repeated computation, and load on slower systems.",
            "Cache correctness depends on expiration, invalidation, freshness, and consistency rules.",
            "Caching introduces tradeoffs between speed, memory use, stale data risk, and complexity.",
        ],
        "examples": ["A web service storing frequent database query results in memory to answer repeated requests quickly."],
        "misconceptions": ["Caching is not free performance; stale or invalid cached data can cause incorrect behavior."],
        "related": ["performance", "invalidation", "latency", "data freshness", "software architecture"],
    },
    "Gravity (Basic Physics)": {
        "definition": "Gravity is the attractive interaction associated with mass and energy that shapes falling motion, weight, planetary orbits, and large-scale structure.",
        "propositions": ["Gravity accelerates objects toward massive bodies.", "Orbital motion can be understood as continuous falling around a central mass.", "Gravity influences both everyday weight and astronomical motion."],
        "examples": ["A satellite remaining in orbit because its forward motion and gravitational fall balance into a curved path."],
        "misconceptions": ["Gravity does not require air or contact; it acts across distance."],
        "related": ["orbital motion", "force", "mass", "acceleration", "projectile motion"],
    },
    "Projectile Motion (Basic Physics)": {
        "definition": "Projectile motion describes the path of an object moving under gravity after launch, often combining horizontal motion with vertical acceleration.",
        "propositions": ["Horizontal and vertical motion can be analyzed separately in simple projectile problems.", "Gravity changes vertical velocity during flight.", "Projectile paths are approximately parabolic when air resistance is ignored."],
        "examples": ["A thrown ball following an arc before returning to the ground."],
        "misconceptions": ["A projectile does not need continued forward force to keep moving horizontally in the idealized model."],
        "related": ["gravity", "velocity", "acceleration", "force vectors", "orbital motion"],
    },
    "Simple Harmonic Motion (Basic Physics)": {
        "definition": "Simple harmonic motion is repeating motion around an equilibrium point where the restoring force is proportional to displacement.",
        "propositions": ["Simple harmonic motion appears in springs, pendulums, and oscillating systems.", "A restoring force pulls the system back toward equilibrium.", "Energy alternates between kinetic and potential forms during the cycle."],
        "examples": ["A mass on a spring oscillating back and forth after being pulled and released."],
        "misconceptions": ["Simple harmonic motion is not any repeated motion; it has a specific proportional restoring-force pattern."],
        "related": ["oscillation", "equilibrium", "energy", "force", "period"],
    },
    "Force Vectors (Basic Physics)": {
        "definition": "Force vectors represent pushes or pulls with both magnitude and direction, allowing multiple forces to be combined and analyzed.",
        "propositions": ["Forces acting in different directions combine according to vector addition.", "Net force determines acceleration in classical mechanics.", "Breaking forces into components helps analyze motion in two or three dimensions."],
        "examples": ["Resolving a ramp force into components parallel and perpendicular to the incline."],
        "misconceptions": ["Force magnitude alone is insufficient; direction changes the resulting motion."],
        "related": ["net force", "acceleration", "projectile motion", "gravity", "engineering constraints"],
    },
    "Constraints (Engineering)": {
        "definition": "Engineering constraints are limits such as cost, safety, materials, time, regulation, or performance that shape feasible design choices.",
        "propositions": ["Constraints narrow the design space.", "Good engineering balances tradeoffs among competing constraints.", "Constraints can be physical, economic, operational, legal, or human."],
        "examples": ["Designing a bridge within load, budget, weather, and safety limits."],
        "misconceptions": ["Constraints are not merely obstacles; they define what a successful design must satisfy."],
        "related": ["tradeoffs", "requirements", "safety factor", "materials", "design"],
    },
    "Fluid Flow (Basic Physics)": {
        "definition": "Fluid flow describes how liquids and gases move in response to pressure differences, gravity, viscosity, and boundary conditions.",
        "propositions": ["Pressure differences can drive fluid motion.", "Viscosity resists flow and dissipates energy.", "Flow behavior depends on geometry, speed, density, and turbulence."],
        "examples": ["Water moving faster through a narrowed section of pipe when pressure conditions allow it."],
        "misconceptions": ["Fluid flow is not determined by pressure alone; geometry and viscosity also matter."],
        "related": ["pressure", "viscosity", "turbulence", "pipes", "engineering"],
    },
    "Blood Pressure (Medicine Health General)": {
        "definition": "Blood pressure is the force exerted by circulating blood against artery walls, usually measured as systolic and diastolic pressure.",
        "propositions": ["Blood pressure reflects heart pumping, vascular resistance, and blood volume.", "Persistently high blood pressure can increase cardiovascular risk.", "Blood pressure varies with activity, stress, posture, and health conditions."],
        "examples": ["A reading of 120/80 mmHg describing pressure during heart contraction and relaxation."],
        "misconceptions": ["A single reading does not fully define cardiovascular health; context and repeated measurement matter."],
        "related": ["fluid pressure", "circulation", "heart", "vascular resistance", "health monitoring"],
    },
    "Pressure (Basic Physics)": {
        "definition": "Pressure is force distributed over area, often describing how fluids push on surfaces or how loads act through contact.",
        "propositions": ["Pressure increases when the same force is applied over a smaller area.", "Fluid pressure can drive flow from higher pressure toward lower pressure.", "Pressure changes can store, transmit, or constrain energy in physical systems."],
        "examples": ["A narrow high heel creating more ground pressure than a flat shoe with the same body weight."],
        "misconceptions": ["Pressure is not the same as total force; area matters."],
        "related": ["force", "area", "fluid flow", "hydraulics", "blood pressure"],
    },
    "Calibration (Engineering)": {
        "definition": "Calibration compares and adjusts a measurement device or process against a known reference so its outputs remain accurate.",
        "propositions": ["Calibration improves confidence in measurements.", "Calibration requires a trusted reference standard.", "Uncalibrated instruments can create systematic error."],
        "examples": ["Adjusting a scale using a known reference weight."],
        "misconceptions": ["Calibration does not make a tool perfect; it reduces known measurement error within limits."],
        "related": ["measurement", "accuracy", "quality control", "engineering constraints", "instrumentation"],
    },
    "Combustion Engines (Energy)": {
        "definition": "Combustion engines convert chemical energy from fuel into heat and mechanical work through controlled burning.",
        "propositions": ["Combustion releases heat by oxidizing fuel.", "Engines convert some thermal energy into mechanical motion.", "Engine efficiency is limited by thermodynamic losses, friction, and heat rejection."],
        "examples": ["A car engine burning gasoline to move pistons and turn a crankshaft."],
        "misconceptions": ["Combustion engines do not convert all fuel energy into useful work; much becomes waste heat."],
        "related": ["thermodynamics", "heat engines", "fuel", "mechanical work", "thermal efficiency"],
    },
    "Baseload (Energy)": {
        "definition": "Baseload is the relatively steady minimum level of electricity demand or generation that persists across a time period.",
        "propositions": ["Baseload demand represents the floor of ongoing electricity use.", "Baseload generation historically came from plants designed to run continuously.", "Modern grids balance baseload with variable renewables, storage, and flexible demand."],
        "examples": ["A city needing a minimum amount of power overnight even when peak daytime demand has ended."],
        "misconceptions": ["Baseload is not the same as total demand; it is the persistent minimum portion."],
        "related": ["grid planning", "energy storage", "demand response", "power generation", "reliability"],
    },
    "Battery Chemistry (Energy)": {
        "definition": "Battery chemistry describes the materials and reactions that store and release electrical energy through electrochemical processes.",
        "propositions": ["Battery chemistry determines voltage, capacity, safety, lifespan, and charging behavior.", "Batteries store energy by moving ions and electrons through controlled reactions.", "Different chemistries trade off cost, density, stability, and performance."],
        "examples": ["Lithium-ion cells storing energy through movement of lithium ions between electrodes."],
        "misconceptions": ["All batteries do not behave the same; chemistry strongly shapes limits and risks."],
        "related": ["energy storage", "electrochemistry", "capacity", "charging", "thermal safety"],
    },
    "Air Filters (Vehicles Mechanics)": {
        "definition": "Air filters remove dust and debris from incoming air before it enters an engine or cabin system.",
        "propositions": ["Engine air filters protect internal components and support proper combustion.", "Clogged filters can reduce airflow and efficiency.", "Cabin filters improve interior air quality by trapping particles."],
        "examples": ["Replacing a dirty engine air filter during routine vehicle maintenance."],
        "misconceptions": ["An air filter is not a performance upgrade by itself; its primary job is controlled filtration."],
        "related": ["maintenance", "combustion engines", "airflow", "vehicle reliability", "filters"],
    },
    "Alternators (Vehicles Mechanics)": {
        "definition": "Alternators generate electrical power in vehicles by converting mechanical rotation into electricity while the engine runs.",
        "propositions": ["Alternators recharge the battery during operation.", "Alternators supply power to electrical systems after the engine starts.", "Alternator failure can cause battery drain and electrical malfunction."],
        "examples": ["A car alternator powering headlights and charging the battery while driving."],
        "misconceptions": ["A car battery does not power everything indefinitely while driving; the alternator carries much of the electrical load."],
        "related": ["vehicle electrical systems", "maintenance", "battery", "mechanical reliability", "energy conversion"],
    },
    "Operator Approval (Delta Architecture Itself)": {
        "definition": "Operator approval is DELTA's requirement that a human explicitly review and allow certain memory, integration, or escalation steps before they occur.",
        "propositions": ["Operator approval prevents casual conversation from becoming automatic memory.", "Approval scopes should be explicit and limited to the current action.", "Approval events support auditability, rollback, and governance."],
        "examples": ["A user accepting a candidate concept before it enters noncanonical memory."],
        "misconceptions": ["Operator approval is not implied by casual agreement unless the current pending action explicitly defines that meaning."],
        "related": ["noncanonical memory", "governance", "audit logs", "rollback", "learning"],
    },
    "Developmental Learning (Delta Architecture Itself)": {
        "definition": "Developmental learning is DELTA's staged approach where conversation forms candidate concepts, review creates reversible knowledge, and mature curricula may later support distillation.",
        "propositions": ["Developmental learning separates day-to-day knowledge growth from neural training.", "Concepts should mature through review, replay, and consolidation before becoming curriculum material.", "Training is treated as a graduation event rather than the default learning mechanism."],
        "examples": ["A useful explanation becoming a reviewed noncanonical concept before any future training packet is considered."],
        "misconceptions": ["Developmental learning is not automatic weight updating; it is governed substrate evolution."],
        "related": ["concept formation", "operator approval", "curriculum", "noncanonical memory", "distillation"],
    },
    "Learning Reinforcement (Psychology)": {
        "definition": "Learning reinforcement is the process by which consequences increase or decrease the likelihood of future behavior or recall.",
        "propositions": ["Reinforcement can strengthen associations and behaviors.", "Feedback timing and consistency affect reinforcement effectiveness.", "Reinforcement can be positive or negative depending on whether something is added or removed."],
        "examples": ["A student practicing more after receiving clear feedback and improvement evidence."],
        "misconceptions": ["Negative reinforcement is not punishment; it strengthens behavior by removing an unpleasant condition."],
        "related": ["behavior change", "feedback loops", "learning", "motivation", "operator review"],
    },
    "Active Listening (Social Communication)": {
        "definition": "Active listening in social communication means attending, reflecting, clarifying, and responding in ways that show accurate understanding.",
        "propositions": ["Active listening reduces misunderstanding by checking meaning before reacting.", "Reflecting and clarifying can de-escalate conflict.", "Active listening supports trust because people feel heard and accurately represented."],
        "examples": ["Saying 'What I hear is...' before responding to a disagreement."],
        "misconceptions": ["Active listening does not require agreeing; it requires understanding before judging."],
        "related": ["communication", "conflict resolution", "empathy", "clarification", "feedback"],
    },
    "Apologies (Social Communication)": {
        "definition": "Apologies are communicative acts that acknowledge harm, responsibility, or regret and can help repair social trust.",
        "propositions": ["Effective apologies usually identify the harm and avoid minimizing responsibility.", "Apologies can reduce conflict when paired with changed behavior.", "An apology may be rejected if it appears insincere or incomplete."],
        "examples": ["Acknowledging a missed deadline, explaining the correction, and committing to a better process."],
        "misconceptions": ["An apology is not just saying sorry; repair often requires accountability and follow-through."],
        "related": ["conflict resolution", "trust repair", "communication", "accountability", "active listening"],
    },
    "Conflict Resolution (Psychology)": {
        "definition": "Conflict resolution is the process of addressing disagreement by clarifying interests, reducing escalation, and finding acceptable next steps.",
        "propositions": ["Conflict resolution works better when parties distinguish positions from underlying interests.", "Listening, evidence, and fair process can reduce defensive reactions.", "Resolution may require compromise, boundaries, repair, or third-party mediation."],
        "examples": ["Two coworkers agreeing on shared priorities after clarifying what each needs from a project handoff."],
        "misconceptions": ["Conflict resolution does not always mean everyone agrees; it may mean a workable boundary or process."],
        "related": ["active listening", "communication", "negotiation", "apologies", "decision-making"],
    },
    "Burnout Prevention (Psychology)": {
        "definition": "Burnout prevention reduces chronic stress and exhaustion by managing workload, recovery, autonomy, support, and expectations.",
        "propositions": ["Burnout risk rises when demands stay high and recovery stays low.", "Prevention includes workload design, boundaries, rest, and social support.", "Burnout prevention benefits from early signals and feedback rather than waiting for collapse."],
        "examples": ["Reducing meeting load and protecting recovery time after sustained overwork."],
        "misconceptions": ["Burnout is not simply laziness or weakness; it often reflects prolonged stress and system conditions."],
        "related": ["stress", "attention", "behavior change", "recovery", "workload"],
    },
    "Energy Efficiency (Energy)": {
        "definition": "Energy efficiency means delivering the same useful service with less energy input by reducing waste and losses.",
        "propositions": ["Efficiency improvements reduce wasted energy.", "Insulation can improve efficiency by reducing heat transfer.", "Efficiency is measured relative to useful output, not total energy use alone."],
        "examples": ["A well-insulated home requiring less heating energy to maintain comfort."],
        "misconceptions": ["Energy efficiency is not the same as using less service; it means less energy for the same or similar service."],
        "related": ["insulation", "thermal efficiency", "energy storage", "heat transfer", "home repair"],
    },
    "Thermal Efficiency (Energy)": {
        "definition": "Thermal efficiency is the fraction of heat energy converted into useful work or useful output rather than lost as waste heat.",
        "propositions": ["Thermal efficiency is constrained by thermodynamics.", "Heat engines reject some heat even when operating well.", "Improving insulation or design can reduce losses in some thermal systems."],
        "examples": ["An engine converting only part of fuel heat into mechanical motion while the rest leaves as exhaust and radiator heat."],
        "misconceptions": ["A thermal system cannot convert all heat into useful work under ordinary heat-engine constraints."],
        "related": ["thermodynamics", "combustion engines", "energy efficiency", "waste heat", "heat transfer"],
    },
    "Insulation (Energy)": {
        "definition": "Insulation reduces heat transfer between regions, helping maintain temperature differences with less energy loss.",
        "propositions": ["Insulation slows conductive, convective, or radiative heat transfer depending on material and design.", "Better insulation can reduce heating and cooling demand.", "Insulation effectiveness depends on installation quality, moisture, air sealing, and material properties."],
        "examples": ["Attic insulation reducing winter heat loss from a house."],
        "misconceptions": ["Insulation does not create heat; it slows unwanted heat movement."],
        "related": ["energy efficiency", "heat transfer", "home repair", "thermal resistance", "building envelope"],
    },
    "Insulation (Home Repair)": {
        "definition": "Home insulation is material installed in walls, attics, floors, or ducts to reduce unwanted heat transfer and improve comfort.",
        "propositions": ["Home insulation can lower heating and cooling energy needs.", "Air leaks can undermine insulation performance.", "Moisture control matters because wet insulation can lose effectiveness or cause damage."],
        "examples": ["Adding attic insulation and sealing gaps around penetrations to reduce heat loss."],
        "misconceptions": ["More insulation is not always useful if air sealing, moisture, or installation problems remain unresolved."],
        "related": ["air sealing", "energy efficiency", "building envelope", "thermal resistance", "home maintenance"],
    },
    "Maintenance Planning (Engineering)": {
        "definition": "Maintenance planning schedules inspections, servicing, replacement, and repairs to keep systems reliable and reduce unexpected failure.",
        "propositions": ["Planned maintenance can reduce downtime and extend asset life.", "Maintenance planning uses condition, usage, risk, and cost information.", "Good maintenance balances prevention costs against failure consequences."],
        "examples": ["Scheduling vehicle oil changes, belt inspections, and brake checks based on mileage and condition."],
        "misconceptions": ["Maintenance planning is not only fixing things after failure; it tries to prevent or prepare for failure."],
        "related": ["mechanical reliability", "risk management", "inspection", "planning", "vehicles mechanics"],
    },
    "Gutter Maintenance (Home Repair)": {
        "definition": "Gutter maintenance keeps roof drainage paths clear and functional so water is directed away from the building.",
        "propositions": ["Blocked gutters can cause overflow, fascia damage, foundation moisture, or roof-edge problems.", "Gutter maintenance includes cleaning debris, checking slope, and inspecting leaks or loose fasteners.", "Drainage performance depends on gutters, downspouts, extensions, and site grading."],
        "examples": ["Clearing leaves from gutters before heavy seasonal rain."],
        "misconceptions": ["Gutters are not cosmetic trim; they are part of a water-control system."],
        "related": ["drainage", "home maintenance", "roof", "foundation protection", "water damage"],
    },
}


def repair_concept_substance(store_path: Path = KNOWLEDGE_MEMORY_LOG) -> dict[str, Any]:
    rows = _read_jsonl(store_path)
    before_by_name = {
        row.get("concept_name"): score_concept_substance(_compact_for_score(row))
        for row in rows
        if row.get("concept_name") in SUBSTANCE_REPAIRS
    }
    repaired = []
    skipped = []
    updated_rows = []
    repaired_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    for row in rows:
        name = str(row.get("concept_name") or "")
        repair = SUBSTANCE_REPAIRS.get(name)
        if not repair:
            updated_rows.append(row)
            continue
        before_score = before_by_name.get(name, score_concept_substance(_compact_for_score(row)))
        if not before_score["generic_definition"] and before_score["score"] >= 0.8:
            skipped.append({"concept_name": name, "reason": "already_substantive", "score": before_score["score"]})
            updated_rows.append(row)
            continue
        new_row = _apply_repair(row, repair, repaired_at)
        after_score = score_concept_substance(_compact_for_score(new_row))
        repaired.append({
            "concept_id": row.get("concept_id"),
            "concept_name": name,
            "score_before": before_score["score"],
            "score_after": after_score["score"],
            "generic_before": before_score["generic_definition"],
            "generic_after": after_score["generic_definition"],
            "rollback_handle": row.get("rollback_handle"),
            "version_handle": new_row.get("substance_repair_version_handle"),
        })
        updated_rows.append(new_row)
    _write_jsonl(store_path, updated_rows)
    synthesis_report = build_synthesis_trial_report()
    return {
        "phase": "RC2.5A Concept Substance Repair",
        "targeted_concepts": len(SUBSTANCE_REPAIRS),
        "repaired_count": len(repaired),
        "skipped_count": len(skipped),
        "repaired": repaired,
        "skipped": skipped,
        "synthesis_quality_after_repair": synthesis_report.get("average_synthesis_quality"),
        "generic_concept_count_after_repair": synthesis_report.get("generic_concept_count"),
        "synthesis_recommendation_after_repair": synthesis_report.get("recommendation"),
        "concept_ids_preserved": all(item["concept_id"] for item in repaired),
        "safety": dict(SAFETY),
        "recommendation": "RERUN_MANUAL_SYNTHESIS_TRIALS_WITH_REPAIRED_CONCEPT_SUBSTANCE",
    }


def write_concept_substance_repair_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    report = repair_concept_substance()
    (REPORTS / "RC2_CONCEPT_SUBSTANCE_REPAIR.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (REPORTS / "RC2_CONCEPT_SUBSTANCE_REPAIR.md").write_text(_report_md(report), encoding="utf-8")
    (DOCS / "continuation_rc2_concept_substance_repair.md").write_text(_continuation_md(report), encoding="utf-8")
    return report


def _apply_repair(row: dict[str, Any], repair: dict[str, Any], repaired_at: str) -> dict[str, Any]:
    previous_digest = _digest(json.dumps({
        "definition": row.get("short_definition"),
        "propositions": row.get("propositions", []),
        "examples": row.get("examples", []),
        "misconceptions": row.get("misconceptions", []),
        "related_concepts": row.get("related_concepts", []),
    }, sort_keys=True))
    new_row = dict(row)
    new_row["short_definition"] = repair["definition"]
    new_row["propositions"] = _merge_unique(repair["propositions"], row.get("propositions", []))
    new_row["examples"] = _merge_unique(repair["examples"], row.get("examples", []))
    new_row["misconceptions"] = _merge_unique(repair["misconceptions"], row.get("misconceptions", []))
    new_row["related_concepts"] = _merge_unique(repair["related"], row.get("related_concepts", []))
    new_row["quality_repair_reason"] = "rc2_5a_concept_substance_repair"
    new_row["substance_repaired_at"] = repaired_at
    new_row["substance_repair_version"] = int(row.get("substance_repair_version") or 0) + 1
    new_row["substance_repair_previous_digest"] = previous_digest
    new_row["substance_repair_version_handle"] = f"rc2-5a-substance-repair-{row.get('concept_id')}-{previous_digest}"
    new_row["canonical"] = False
    new_row["training_performed"] = False
    new_row["provider_calls_performed"] = False
    return new_row


def _compact_for_score(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_name": row.get("concept_name"),
        "short_definition": row.get("short_definition"),
        "propositions": row.get("propositions", []),
        "examples": row.get("examples", []),
        "misconceptions": row.get("misconceptions", []),
        "related_concepts": row.get("related_concepts", []),
    }


def _merge_unique(primary: list[str], existing: object) -> list[str]:
    merged = []
    seen = set()
    for item in [*primary, *(existing if isinstance(existing, list) else [])]:
        text = str(item or "").strip()
        if not text:
            continue
        key = " ".join(text.lower().split())
        if key in seen:
            continue
        seen.add(key)
        merged.append(text)
    return merged


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _report_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2.5A Concept Substance Repair",
        "",
        f"Targeted concepts: {report['targeted_concepts']}",
        f"Repaired concepts: {report['repaired_count']}",
        f"Skipped concepts: {report['skipped_count']}",
        f"Synthesis quality after repair: {report['synthesis_quality_after_repair']}",
        f"Generic concept count after repair: {report['generic_concept_count_after_repair']}",
        "",
        "## Repaired Concepts",
        "",
    ]
    for item in report["repaired"]:
        lines.append(f"- {item['concept_name']}: {item['score_before']} -> {item['score_after']}")
    lines.extend(["", f"Recommendation: {report['recommendation']}"])
    return "\n".join(lines) + "\n"


def _continuation_md(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Continuation: RC2.5A Concept Substance Repair",
        "",
        "Concept substance repair targeted synthesis-trial inputs only.",
        "Concept IDs and rollback handles were preserved; updates remain noncanonical and reversible.",
        f"Repaired concepts: {report['repaired_count']}",
        f"Generic concept count after repair: {report['generic_concept_count_after_repair']}",
        f"Synthesis quality after repair: {report['synthesis_quality_after_repair']}",
        "",
        "Next: rerun manual read-only synthesis trials and inspect whether bridges now cite richer stored substance.",
    ]) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_concept_substance_repair_reports(), indent=2, sort_keys=True))
