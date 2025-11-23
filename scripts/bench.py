import asyncio
import os
import sys
import tkinter as tk
from tkinter import ttk
from dotenv import load_dotenv

load_dotenv()

from agi_agents.qwen.qwen import QwenAgent
from arena import RunHarness


def select_tasks_gui():
    """
    Opens a GUI to select tasks from the benchmarks directory.
    Returns a list of selected task filenames.
    """
    # Determine path to tasks directory
    # Assuming script is run from project root or scripts dir
    possible_paths = [
        os.path.join("src", "benchmarks", "hackathon", "tasks"),
        os.path.join("..", "src", "benchmarks", "hackathon", "tasks"),
    ]
    
    tasks_dir = None
    for p in possible_paths:
        if os.path.exists(p):
            tasks_dir = p
            break
            
    if not tasks_dir:
        print("Error: Could not find tasks directory.")
        return []

    # Get list of json files
    try:
        files = sorted([f for f in os.listdir(tasks_dir) if f.endswith('.json')])
    except OSError as e:
        print(f"Error reading tasks directory: {e}")
        return []

    if not files:
        print("No task files found in directory.")
        return []

    selected_files = []
    
    # Create GUI
    try:
        root = tk.Tk()
        root.title("Benchmark Selection")
        root.geometry("500x600")
        
        # Style
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TCheckbutton", font=("Arial", 10))

        # Main container
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Label(main_frame, text="Select Tasks to Run", font=("Arial", 14, "bold"))
        header.pack(pady=(0, 10), anchor="w")
        
        subtext = ttk.Label(main_frame, text=f"Found {len(files)} tasks in {tasks_dir}", font=("Arial", 9, "italic"))
        subtext.pack(pady=(0, 10), anchor="w")

        # List area with scrollbar
        list_frame = ttk.Frame(main_frame, relief="sunken", borderwidth=1)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        canvas = tk.Canvas(list_frame, bg="white")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="White.TFrame")
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Populate checkboxes
        vars = []
        for f in files:
            var = tk.BooleanVar(value=False)
            # Frame for row to help with layout
            row = ttk.Frame(scrollable_frame)
            row.pack(fill='x', padx=5, pady=2)
            
            chk = ttk.Checkbutton(row, text=f, variable=var)
            chk.pack(anchor='w')
            vars.append((f, var))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Button area
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        def select_all():
            for _, var in vars:
                var.set(True)

        def select_none():
            for _, var in vars:
                var.set(False)

        ttk.Button(btn_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Clear", command=select_none).pack(side=tk.LEFT)

        def on_run():
            for f, var in vars:
                if var.get():
                    selected_files.append(f)
            root.quit()
            root.destroy()

        run_btn = ttk.Button(btn_frame, text="Run Selected", command=on_run)
        run_btn.pack(side=tk.RIGHT)
        
        # Focus window
        root.focus_force()
        
        root.mainloop()
        
    except Exception as e:
        print(f"Failed to launch GUI: {e}")
        # Fallback?
        return []

    return selected_files


async def main(tasks=None):
    if not tasks:
        print("No tasks provided. Exiting.")
        return

    print(f"Starting benchmark with {len(tasks)} tasks...")
    
    agent = QwenAgent()

    harness = RunHarness(
        agent=agent,
        tasks=tasks,
        parallel=60, # was 60
        sample_count=1,
        max_steps=int(os.getenv("MAX_STEPS", "60")),
        headless=True
    )

    results = await harness.run()
    
    # Print summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    
    total_tasks = len(results)
    successful_tasks = 0
    
    for i, result in enumerate(results):
        if not result:
             continue
        # Result is an ExperimentResult object, likely containing details in .details list/tuple
        details = getattr(result, "details", [])
        task_info = details[0] if details and len(details) > 0 else {}
        
        task_name = task_info.get("goal", f"Task {i+1}")
        # Shorten task name if too long
        if len(task_name) > 80:
            task_name = task_name[:77] + "..."

        is_success = result.success
        if is_success:
            successful_tasks += 1
        status = "PASS" if is_success else "FAIL"
        
        # Extract criteria info
        criteria_info = ""
        passed_crit = task_info.get("passed_criteria")
        total_crit = task_info.get("total_criteria")
        
        if passed_crit is not None and total_crit is not None:
            criteria_info = f" ({passed_crit}/{total_crit} criteria)"
            
        print(f"Task: {task_name}")
        print(f"Status: {status}{criteria_info}")
        print("-" * 30)

    print(f"\nTotal: {successful_tasks}/{total_tasks} tasks passed")
    print("="*60)

if __name__ == "__main__":
    # Allow passing tasks via command line args to bypass GUI
    if len(sys.argv) > 1:
        selected_tasks = sys.argv[1:]
    else:
        selected_tasks = select_tasks_gui()
    
    if selected_tasks:
        asyncio.run(main(selected_tasks))
    else:
        print("No tasks selected.")
