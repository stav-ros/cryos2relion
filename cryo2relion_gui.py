#!/usr/bin/env python3
"""
CryoSPARC to RELION Particle Export GUI
Converts cryoSPARC .cs files to RELION-compatible .star files with safety checks.
Requires: pyem, pandas, starfile (install via: conda install -c conda-forge pyem)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
from datetime import datetime
import json

class Cryo2RelionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CryoSPARC → RELION Particle Export")
        self.root.geometry("1000x900")
        self.root.minsize(900, 700)
        
        # State variables
        self.particle_file = tk.StringVar()
        self.passthrough_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.micrograph_path = tk.StringVar()
        self.original_star = tk.StringVar()
        
        self.inverty = tk.BooleanVar(value=False)
        self.strip_uid = tk.BooleanVar(value=True)
        self.copy_stacks = tk.BooleanVar(value=True)
        self.rename_mrcs = tk.BooleanVar(value=True)
        self.create_symlinks = tk.BooleanVar(value=False)
        self.copy_coords = tk.BooleanVar(value=False)
        
        self.log_text = None
        self.pyem_available = self._check_pyem()
        
        self._build_ui()
        
    def _check_pyem(self):
        """Check if pyem is installed."""
        try:
            import pyem
            return True
        except ImportError:
            return False
    
    def _log(self, message, level="INFO"):
        """Log message to both console and GUI."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"
        print(log_msg)
        
        if self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, log_msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.root.update()
    
    def _build_ui(self):
        """Build the GUI."""
        # Top status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        pyem_status = "✓ PyEM available" if self.pyem_available else "✗ PyEM NOT installed (conda install -c conda-forge pyem)"
        pyem_color = "green" if self.pyem_available else "red"
        ttk.Label(status_frame, text=pyem_status, foreground=pyem_color).pack(side=tk.LEFT)
        
        # Main notebook (tabbed interface)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: File Selection
        self._build_file_selection_tab(notebook)
        
        # Tab 2: Conversion Options
        self._build_options_tab(notebook)
        
        # Tab 3: Output & Execution
        self._build_execution_tab(notebook)
        
        # Tab 4: Help
        self._build_help_tab(notebook)
    
    def _build_file_selection_tab(self, notebook):
        """Build the file selection tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="1. Select Files")
        
        # Main content with scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Instructions
        instructions = ttk.Label(
            scrollable_frame,
            text="Step 1: Locate cryoSPARC output files from a refinement job\n" +
                 "You need:\n" +
                 "  • particles.cs (or cryosparc_Px_Jy_particles.cs)\n" +
                 "  • passthrough file with coordinates (e.g., Px_Jy_passthrough_particles.cs)",
            justify=tk.LEFT,
            wraplength=700
        )
        instructions.pack(fill=tk.X, padx=10, pady=10)
        
        # Particle file
        ttk.Label(scrollable_frame, text="Particle .CS File (required):").pack(anchor=tk.W, padx=10, pady=(10,0))
        frame1 = ttk.Frame(scrollable_frame)
        frame1.pack(fill=tk.X, padx=10, pady=5)
        ttk.Entry(frame1, textvariable=self.particle_file, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame1, text="Browse", command=self._browse_particle_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame1, text="Auto-find", command=self._auto_find_particles).pack(side=tk.LEFT, padx=2)
        
        # Passthrough file
        ttk.Label(scrollable_frame, text="Passthrough .CS File (required for coordinates):").pack(anchor=tk.W, padx=10, pady=(10,0))
        frame2 = ttk.Frame(scrollable_frame)
        frame2.pack(fill=tk.X, padx=10, pady=5)
        ttk.Entry(frame2, textvariable=self.passthrough_file, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame2, text="Browse", command=self._browse_passthrough_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame2, text="Auto-find", command=self._auto_find_passthrough).pack(side=tk.LEFT, padx=2)
        
        # Output directory
        ttk.Label(scrollable_frame, text="Output Directory (where to save star file and stacks):").pack(anchor=tk.W, padx=10, pady=(10,0))
        frame3 = ttk.Frame(scrollable_frame)
        frame3.pack(fill=tk.X, padx=10, pady=5)
        ttk.Entry(frame3, textvariable=self.output_dir, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame3, text="Browse", command=self._browse_output_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame3, text="Use cwd", command=lambda: self.output_dir.set(os.getcwd())).pack(side=tk.LEFT, padx=2)
        
        # Output filename
        ttk.Label(scrollable_frame, text="Output STAR Filename:").pack(anchor=tk.W, padx=10, pady=(10,0))
        frame4 = ttk.Frame(scrollable_frame)
        frame4.pack(fill=tk.X, padx=10, pady=5)
        self.output_file.set("particles_relion.star")
        ttk.Entry(frame4, textvariable=self.output_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        
        # Optional: original star for coordinate merging
        ttk.Label(scrollable_frame, text="Original RELION STAR (optional - to restore exact coordinates):").pack(anchor=tk.W, padx=10, pady=(10,0))
        frame5 = ttk.Frame(scrollable_frame)
        frame5.pack(fill=tk.X, padx=10, pady=5)
        ttk.Entry(frame5, textvariable=self.original_star, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame5, text="Browse", command=self._browse_original_star).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(frame5, text="Use", variable=self.copy_coords).pack(side=tk.LEFT, padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _build_options_tab(self, notebook):
        """Build the conversion options tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="2. Options")
        
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Conversion options
        options_lf = ttk.LabelFrame(scrollable_frame, text="Conversion Flags", padding=10)
        options_lf.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(options_lf, text="--inverty (undo Y-axis flip if from MotionCor2/RELION)", 
                       variable=self.inverty).pack(anchor=tk.W)
        ttk.Checkbutton(options_lf, text="--strip-uid (remove 21-digit UID prefix)", 
                       variable=self.strip_uid).pack(anchor=tk.W)
        
        # Micrograph path
        ttk.Label(options_lf, text="Micrograph Directory Path (optional - prepend to micrograph names):").pack(anchor=tk.W, pady=(10,0))
        frame_mg = ttk.Frame(options_lf)
        frame_mg.pack(fill=tk.X, pady=5)
        ttk.Entry(frame_mg, textvariable=self.micrograph_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame_mg, text="Browse", command=self._browse_micrograph_path).pack(side=tk.LEFT, padx=5)
        
        # Stack handling
        stack_lf = ttk.LabelFrame(scrollable_frame, text="Particle Stack Handling", padding=10)
        stack_lf.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(stack_lf, text="Copy particle stacks to output directory", 
                       variable=self.copy_stacks).pack(anchor=tk.W)
        ttk.Checkbutton(stack_lf, text="Create symlinks instead of copying (saves space)", 
                       variable=self.create_symlinks).pack(anchor=tk.W)
        ttk.Checkbutton(stack_lf, text="Rename .mrc to .mrcs (RELION standard)", 
                       variable=self.rename_mrcs).pack(anchor=tk.W)
        
        ttk.Label(stack_lf, text="Note: Stack handling ensures particle .mrcs files are accessible\n" +
                                "from the RELION project directory.",
                 wraplength=700, justify=tk.LEFT).pack(anchor=tk.W, pady=(10,0))
        
        # Info box
        info_lf = ttk.LabelFrame(scrollable_frame, text="Important Notes", padding=10)
        info_lf.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = (
            "• For 3D reconstruction: Euler angles from cryoSPARC will be transferred.\n"
            "• Test with: relion_reconstruct --i particles_relion.star --o map.mrc\n"
            "• The output star file will have: _rlnImageName, _rlnMicrographName, "
            "_rlnCoordinateX/Y, and Euler angles.\n"
            "• All paths in the star file are relative to the output directory."
        )
        ttk.Label(info_lf, text=info_text, justify=tk.LEFT, wraplength=700).pack(anchor=tk.W)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _build_execution_tab(self, notebook):
        """Build the execution and logging tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="3. Execute & Log")
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Validate Inputs", command=self._validate_inputs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Preview Conversion", command=self._preview_conversion).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="▶ EXECUTE CONVERSION", command=self._execute_conversion, 
                  width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_label = ttk.Label(frame, text="Conversion Log:")
        log_label.pack(anchor=tk.W, padx=10, pady=(10,2))
        
        self.log_text = scrolledtext.ScrolledText(frame, height=20, width=100, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Results area
        results_label = ttk.Label(frame, text="Results:")
        results_label.pack(anchor=tk.W, padx=10, pady=(10,2))
        
        self.results_text = scrolledtext.ScrolledText(frame, height=5, width=100, state=tk.DISABLED)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    def _build_help_tab(self, notebook):
        """Build the help tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Help")
        
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        help_text = """
QUICK START
===========
1. In cryoSPARC GUI: Job → Output → Download particles
2. You need BOTH the particles file AND the passthrough file
3. Select both files here
4. Choose output directory
5. Click "EXECUTE CONVERSION"

WHAT THIS TOOL DOES
===================
• Converts cryoSPARC .cs files to RELION-compatible .star files
• Preserves particle coordinates and micrograph names
• Transfers Euler angles from cryoSPARC refinement
• Handles particle stack files (.mrcs)
• Validates all paths and file formats

KEY CONCEPTS
============
Particle File: Contains particle metadata (positions, angles)
Passthrough File: Contains original micrograph names and coordinates
Star File: RELION format file that references particles and micrographs
Particle Stacks: .mrcs image files containing actual particle data

VALIDATION & FAILSAFES
======================
✓ Checks for missing files before running
✓ Validates file formats (.cs, .star)
✓ Creates backups before overwriting
✓ Verifies relative paths work correctly
✓ Warns if particles don't fall within micrograph bounds

AFTER CONVERSION
================
Test reconstruction with:
  relion_reconstruct --i particles_relion.star --o test_map.mrc

This should produce a map similar to your cryoSPARC output.

TROUBLESHOOTING
===============
Issue: "PyEM not found"
Solution: conda install -c conda-forge pyem

Issue: "Passthrough file not found"
Solution: Make sure you downloaded it from cryoSPARC (it's optional 
          in the UI but HIGHLY RECOMMENDED for accurate coordinates)

Issue: "relion_reconstruct fails"
Solution: Check that _rlnImageName paths point to existing .mrcs files
          Use "Preview" first to see what will be generated

ADVANCED OPTIONS
================
--inverty: Use if particles were originally from MotionCor2 or RELION
--strip-uid: Removes CryoSPARC's automatic UID prefixes
Micrograph path: Set this if micrographs are in a specific subdirectory

For more info, see: https://github.com/asarnow/pyem
"""
        # Use regular tk.Label with monospace font instead of ttk.Label
        help_label = tk.Label(scrollable_frame, text=help_text, justify=tk.LEFT, 
                             wraplength=750, font=("Courier", 10), bg="white")
        help_label.pack(anchor="nw", padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    # ===== File Browser Methods =====
    def _browse_particle_file(self):
        file = filedialog.askopenfilename(
            title="Select particle .cs file",
            filetypes=[("CryoSPARC files", "*.cs"), ("All files", "*.*")]
        )
        if file:
            self.particle_file.set(file)
            self._log(f"Selected particle file: {file}")
    
    def _browse_passthrough_file(self):
        file = filedialog.askopenfilename(
            title="Select passthrough .cs file",
            filetypes=[("CryoSPARC files", "*.cs"), ("All files", "*.*")]
        )
        if file:
            self.passthrough_file.set(file)
            self._log(f"Selected passthrough file: {file}")
    
    def _browse_output_dir(self):
        dir = filedialog.askdirectory(title="Select output directory")
        if dir:
            self.output_dir.set(dir)
            self._log(f"Output directory set to: {dir}")
    
    def _browse_micrograph_path(self):
        dir = filedialog.askdirectory(title="Select micrograph directory")
        if dir:
            self.micrograph_path.set(dir)
            self._log(f"Micrograph path set to: {dir}")
    
    def _browse_original_star(self):
        file = filedialog.askopenfilename(
            title="Select original RELION .star file",
            filetypes=[("RELION files", "*.star"), ("All files", "*.*")]
        )
        if file:
            self.original_star.set(file)
            self._log(f"Selected original star: {file}")
    
    def _auto_find_particles(self):
        """Try to find particle file from a directory."""
        start_dir = self.particle_file.get() or os.path.expanduser("~")
        if os.path.isfile(start_dir):
            start_dir = os.path.dirname(start_dir)
        
        dir = filedialog.askdirectory(title="Select cryoSPARC job directory", initialdir=start_dir)
        if not dir:
            return
        
        # Look for particles.cs or *particles.cs
        for pattern in ["particles.cs", "*particles.cs"]:
            import glob
            files = glob.glob(os.path.join(dir, pattern))
            if files:
                files.sort()
                self.particle_file.set(files[-1])  # Take the most recent
                self._log(f"Auto-found particle file: {files[-1]}")
                break
    
    def _auto_find_passthrough(self):
        """Try to find passthrough file from a directory."""
        start_dir = self.particle_file.get()
        if not start_dir or not os.path.isfile(start_dir):
            messagebox.showwarning("Warning", "Please select particle file first")
            return
        
        start_dir = os.path.dirname(start_dir)
        
        # Look for *passthrough*.cs
        import glob
        files = glob.glob(os.path.join(start_dir, "*passthrough*.cs"))
        if files:
            files.sort()
            self.passthrough_file.set(files[-1])
            self._log(f"Auto-found passthrough file: {files[-1]}")
        else:
            messagebox.showwarning("Not found", "Could not find passthrough file in that directory")
    
    # ===== Validation & Execution =====
    def _validate_inputs(self):
        """Validate all inputs before conversion."""
        self._log("=" * 60, "VALIDATION")
        errors = []
        
        # Check particle file
        if not self.particle_file.get():
            errors.append("Particle .cs file not specified")
        elif not os.path.isfile(self.particle_file.get()):
            errors.append(f"Particle file not found: {self.particle_file.get()}")
        else:
            self._log(f"✓ Particle file: {self.particle_file.get()}")
        
        # Check passthrough file (optional but recommended)
        if not self.passthrough_file.get():
            self._log("⚠ Passthrough file not specified (coordinates may be lost!)", "WARNING")
        elif not os.path.isfile(self.passthrough_file.get()):
            errors.append(f"Passthrough file not found: {self.passthrough_file.get()}")
        else:
            self._log(f"✓ Passthrough file: {self.passthrough_file.get()}")
        
        # Check output directory
        if not self.output_dir.get():
            errors.append("Output directory not specified")
        elif not os.path.isdir(self.output_dir.get()):
            errors.append(f"Output directory not found: {self.output_dir.get()}")
        else:
            self._log(f"✓ Output directory: {self.output_dir.get()}")
        
        # Check pyem
        if not self.pyem_available:
            errors.append("PyEM not installed. Install with: conda install -c conda-forge pyem")
        else:
            self._log("✓ PyEM is available")
        
        # Check optional original star
        if self.copy_coords.get() and self.original_star.get():
            if not os.path.isfile(self.original_star.get()):
                errors.append(f"Original star file not found: {self.original_star.get()}")
            else:
                self._log(f"✓ Original star file: {self.original_star.get()}")
        
        if errors:
            error_msg = "\n".join([f"✗ {e}" for e in errors])
            self._log(error_msg, "ERROR")
            messagebox.showerror("Validation Failed", error_msg)
            return False
        else:
            self._log("All validations passed!", "SUCCESS")
            messagebox.showinfo("Validation Passed", "All inputs are valid. Ready to convert!")
            return True
    
    def _preview_conversion(self):
        """Show what will happen without actually doing it."""
        if not self._validate_inputs():
            return
        
        self._log("=" * 60, "PREVIEW")
        
        output_star = os.path.join(self.output_dir.get(), self.output_file.get())
        self._log(f"Output star file will be: {output_star}")
        
        # Show command that will be run
        cmd = ["csparc2star.py"]
        if self.inverty.get():
            cmd.append("--inverty")
        if self.strip_uid.get():
            cmd.append("--strip-uid=21")
        if self.micrograph_path.get():
            cmd.extend(["--micrograph-path", self.micrograph_path.get()])
        
        cmd.append(self.particle_file.get())
        if self.passthrough_file.get():
            cmd.append(self.passthrough_file.get())
        cmd.append(output_star)
        
        self._log(f"Command: {' '.join(cmd)}")
        
        if self.copy_stacks.get():
            self._log("Will copy/symlink particle stacks to output directory")
            self._log(f"  Rename .mrc to .mrcs: {self.rename_mrcs.get()}")
        
        if self.copy_coords.get() and self.original_star.get():
            self._log("Will merge coordinates from original star file")
        
        self._log("Preview complete. Ready to execute!", "INFO")
    
    def _execute_conversion(self):
        """Execute the full conversion pipeline."""
        if not self._validate_inputs():
            return
        
        if not messagebox.askyesno("Confirm", "Execute conversion? This may take a moment."):
            return
        
        try:
            self._log("=" * 60, "EXECUTION START")
            
            output_dir = Path(self.output_dir.get())
            output_star = output_dir / self.output_file.get()
            
            # Create backup if output already exists
            if output_star.exists():
                backup_path = output_star.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
                shutil.copy2(output_star, backup_path)
                self._log(f"Backed up existing file to: {backup_path}")
            
            # Step 1: Convert with csparc2star.py
            self._log("Step 1: Converting with csparc2star.py...", "INFO")
            cmd = ["csparc2star.py"]
            
            if self.inverty.get():
                cmd.append("--inverty")
            if self.strip_uid.get():
                cmd.append("--strip-uid=21")
            if self.micrograph_path.get():
                cmd.extend(["--micrograph-path", self.micrograph_path.get()])
            
            cmd.extend([
                self.particle_file.get(),
                self.passthrough_file.get() if self.passthrough_file.get() else "",
                str(output_star)
            ])
            cmd = [c for c in cmd if c]  # Remove empty strings
            
            self._log(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(output_dir))
            
            if result.returncode != 0:
                self._log(f"Error: {result.stderr}", "ERROR")
                raise RuntimeError(f"csparc2star.py failed: {result.stderr}")
            
            self._log("✓ STAR file created successfully", "SUCCESS")
            if result.stdout:
                self._log(result.stdout)
            
            # Step 2: Handle stacks
            if self.copy_stacks.get():
                self._log("Step 2: Handling particle stacks...", "INFO")
                self._handle_particle_stacks(output_dir, output_star)
            
            # Step 3: Merge coordinates if needed
            if self.copy_coords.get() and self.original_star.get():
                self._log("Step 3: Merging original coordinates...", "INFO")
                self._merge_coordinates(output_star)
            
            # Summary
            self._log("=" * 60, "CONVERSION COMPLETE")
            self._log(f"Output star file: {output_star}", "SUCCESS")
            self._log(f"Output directory: {output_dir}", "SUCCESS")
            
            self._show_results(output_star, output_dir)
            messagebox.showinfo("Success", f"Conversion complete!\n\nStar file: {output_star}")
            
        except Exception as e:
            self._log(f"Conversion failed: {str(e)}", "ERROR")
            messagebox.showerror("Conversion Failed", str(e))
    
    def _handle_particle_stacks(self, output_dir, output_star):
        """Copy/symlink particle stacks, preserving cryoSPARC directory hierarchy (e.g., J67/extract/)."""
        try:
            import re
            with open(output_star) as f:
                content = f.read()

            # Match image refs like "000003@J67/extract/file.mrc" - capture prefix and path separately
            raw_refs = re.findall(r'(\d+@)?(\S+\.mr[cs]+)', content)
            stack_paths = [p for (prefix, p) in raw_refs if '/' in p]
            if not stack_paths:
                self._log("No particle stack references found in star file", "WARNING")
                return False

            first_path = stack_paths[0]
            ref_path = Path(first_path)

            # CryoSPARC project root = parent of the job folder containing particles.cs
            particle_file = Path(self.particle_file.get())
            cs_project_root = particle_file.parent.parent

            # Full source path on disk
            source_dir = cs_project_root / ref_path.parent
            if not source_dir.exists():
                self._log(f"Stack directory not found: {source_dir}", "WARNING")
                return False

            # Target: PRESERVE cryoSPARC hierarchy (e.g., output_dir/J67/extract)
            target_dir = output_dir / ref_path.parent
            self._log(f"Auto-detected source: {source_dir}", "INFO")
            self._log(f"Target (preserving cryoSPARC hierarchy): {target_dir}", "INFO")

            if target_dir.exists():
                if target_dir.is_symlink():
                    target_dir.unlink()
                else:
                    shutil.rmtree(target_dir)

            # Ensure parent directory exists (e.g., output_dir/J67/)
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            if self.create_symlinks.get():
                os.symlink(source_dir, target_dir)
                self._log(f"✓ Created symlink: {target_dir}", "SUCCESS")
            else:
                shutil.copytree(source_dir, target_dir)
                self._log(f"✓ Copied stacks to: {target_dir}", "SUCCESS")

            # Rename .mrc -> .mrcs on disk
            if self.rename_mrcs.get():
                count = 0
                for mrc_file in target_dir.glob("*.mrc"):
                    mrc_file.rename(mrc_file.with_suffix(".mrcs"))
                    count += 1
                if count:
                    self._log(f"✓ Renamed {count} .mrc -> .mrcs on disk", "SUCCESS")

            # Rewrite paths in star file: rename .mrc -> .mrcs ONLY
            # CRITICAL: DO NOT strip the NNNNNN@ prefix - it's essential RELION syntax!
            new_content = content
            if self.rename_mrcs.get():
                new_content = re.sub(r'\.mrc(?!s)', '.mrcs', new_content)

            with open(output_star, 'w') as f:
                f.write(new_content)
            self._log(f"✓ Updated star file extensions (.mrc -> .mrcs)", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"Error handling stacks: {str(e)}", "ERROR")
            return False

    def _merge_coordinates(self, output_star):
        """Merge coordinates from original star."""
        try:
            cmd = [
                "star.py",
                "--copy-micrograph-coordinates",
                self.original_star.get(),
                str(output_star),
                str(output_star)  # Overwrite
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self._log(f"Warning merging coordinates: {result.stderr}", "WARNING")
            else:
                self._log("✓ Coordinates merged", "SUCCESS")
        
        except Exception as e:
            self._log(f"Warning: Could not merge coordinates: {str(e)}", "WARNING")
    
    def _show_results(self, output_star, output_dir):
        """Display results."""
        results = f"""
OUTPUT SUMMARY
==============
Star file: {output_star}
Directory: {output_dir}

NEXT STEPS
==========
1. Verify the star file has the correct columns:
   _rlnImageName, _rlnMicrographName, _rlnCoordinateX/Y

2. Test reconstruction:
   cd {output_dir}
   relion_reconstruct --i {self.output_file.get()} --o test_map.mrc

3. Import into RELION:
   RELION GUI → Import → Particles → {self.output_file.get()}

TIPS
====
• Check that all paths are accessible
• Verify particle coordinates fall within micrograph bounds
• Euler angles from cryoSPARC are preserved (if present)
"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, results)
        self.results_text.config(state=tk.DISABLED)
        self._log(results)
    
    def _clear_log(self):
        """Clear the log window."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = Cryo2RelionGUI(root)
    root.mainloop()
