import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def generate_data_flow_image():
    out_dir = Path("reports/images")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(15, 8.5), facecolor='#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # Title
    ax.text(50, 95, "TIRELESS HAND: END-TO-END AUTONOMOUS DATA FLOW", 
            fontsize=18, fontweight='bold', color='#38BDF8', ha='center', va='center', fontfamily='sans-serif')
    ax.text(50, 91, "Multi-Viewport Layout, In-Flight CDP Observers, Invariant Engines & Dual Verification Pipeline", 
            fontsize=10.5, color='#94A3B8', ha='center', va='center')
    
    # Box styles
    def draw_box(x, y, w, h, title, subtitle, items, bg_color, border_color, title_color='#38BDF8'):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1.2", 
                                     facecolor=bg_color, edgecolor=border_color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 2.5, title, fontsize=11, fontweight='bold', color=title_color, ha='center', va='top')
        if subtitle:
            ax.text(x + w/2, y + h - 5.5, subtitle, fontsize=8.5, color='#CBD5E1', ha='center', va='top', style='italic')
        
        curr_y = y + h - 9.0
        for item in items:
            ax.text(x + 2, curr_y, f"• {item}", fontsize=8.2, color='#E2E8F0', va='top')
            curr_y -= 3.2

    # Draw Stage 1: Ingestion
    draw_box(3, 50, 20, 34, "1. TARGET INGESTION", "Real & Mutated Cockpits", 
             ["FlytBase React 18 / Vite", "CesiumJS 3D WebGL Globe", "Telemetry WebSockets / REST", "Fault Injection Labs", "Dynamic State Mutants"],
             '#1E293B', '#3B82F6', '#60A5FA')

    # Draw Stage 2: Observers
    draw_box(26.5, 50, 21, 34, "2. CDP OBSERVERS", "In-Flight Zero-Overhead", 
             ["Playwright Chromium CDP", "Compact Accessibility Tree", "LCP / CLS Layout Shift Mon", "Heap & Long-Task (>50ms)", "60 FPS Frame Rate Tracker"],
             '#1E1B4B', '#8B5CF6', '#A78BFA')

    # Draw Stage 3: Invariant Analyzer
    draw_box(51, 50, 22.5, 34, "3. AUTONOMOUS CORE", "Invariant Engines & AI", 
             ["Level 1 Static & Auth Invariants", "Level 2 Telemetry & Heap Perf", "6-Signal Self-Healing (ID/ARIA)", "Root-Cause Reasoner", "Automated Severity Scoring"],
             '#064E3B', '#10B981', '#34D399')

    # Draw Stage 4: Live HUD
    draw_box(76.5, 50, 20.5, 34, "4. REAL-TIME HUD", "Live Console & API", 
             ["FastAPI / Uvicorn Server (:8000)", "Glassmorphic Web HUD (/ui)", "Chart.js Matrix Graphs", "60 FPS Oscilloscope Canvas", "One-Click Audit Triggers"],
             '#312E81', '#6366F1', '#818CF8')

    # Draw Stage 5: Outputs (Bottom Row)
    draw_box(6, 6, 26, 32, "5A. WORD SUBMISSIONS", "Formal Evaluation Deliverables",
             ["Tireless_Hand_Level1_Submission.docx", "Tireless_Hand_Level2_Submission.docx", "Embedded High-Res Binary Charts", "100% Precision / Recall Tables", "Root-Cause & Fix Evidence"],
             '#4A044E', '#D946EF', '#F472B6')

    draw_box(37, 6, 26, 32, "5B. AI DEMO VIDEOS", "Synthesized Voice & Screencast",
             ["tireless_hand_level2_demo.mp4", "tireless_hand_level2_demo.webm", "60s Synchronized Narration", "Neural AI Voice (en-US)", "Live Dashboard & Matrix Walkthrough"],
             '#4C0519', '#F43F5E', '#FB7185')

    draw_box(68, 6, 26, 32, "5C. EVIDENCE REPORTS", "Zero-Artifact Visual Snapshots",
             ["reports/submission.html (Cards)", "reports/screenshots/ (PNG)", "reports/videos/ (Interactive WebM)", "Zero-Overhead Memory Snapshots", "Automated Playback Flushes"],
             '#14532D', '#22C55E', '#4ADE80')

    # Draw arrows between top stages
    def draw_arrow(x1, y1, x2, y2, color='#38BDF8', text=""):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(facecolor=color, edgecolor=color, width=2.5, headwidth=8, headlength=7, shrink=0.05))
        if text:
            ax.text((x1+x2)/2, (y1+y2)/2 + 2, text, fontsize=7.5, color='#94A3B8', ha='center', va='bottom', fontweight='bold')

    draw_arrow(23, 67, 26.5, 67, '#3B82F6', "Stream")
    draw_arrow(47.5, 67, 51, 67, '#8B5CF6', "Telemetry")
    draw_arrow(73.5, 67, 76.5, 67, '#10B981', "Events")

    # Downward branching arrows to outputs
    draw_arrow(62, 50, 19, 38, '#D946EF')
    draw_arrow(62, 50, 50, 38, '#F43F5E')
    draw_arrow(62, 50, 81, 38, '#22C55E')

    plt.tight_layout()
    output_path = out_dir / "system_data_flow.png"
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"[+] Saved system data flow diagram to {output_path}")

if __name__ == "__main__":
    generate_data_flow_image()
