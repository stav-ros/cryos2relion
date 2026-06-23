#!/usr/bin/env python3
"""
CryoSPARC to RELION Command-Line Interface
Alternative to GUI for scripting, HPC pipelines, and batch processing.

Usage:
  cryo2relion_cli.py --particles particles.cs --passthrough pass.cs --output out.star
  cryo2relion_cli.py --help
"""

import argparse
import sys
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import logging

class Cryo2RelionCLI:
    def __init__(self, args):
        self.args = args
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging."""
        logger = logging.getLogger("cryo2relion")
        logger.setLevel(logging.DEBUG if self.args.verbose else logging.INFO)
        
        # Console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.args.verbose else logging.INFO)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # File handler
        if self.args.log_file:
            fh = logging.FileHandler(self.args.log_file)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        
        return logger
    
    def log(self, msg, level="INFO"):
        """Log message."""
        level_lower = level.lower(); getattr(self.logger, "info" if level_lower == "success" else level_lower)(msg)
    
    def validate_inputs(self):
        """Validate all inputs."""
        self.log("=" * 60, "INFO")
        self.log("VALIDATION", "INFO")
        self.log("=" * 60, "INFO")
        
        errors = []
        
        # Check particle file
        if not self.args.particles:
            errors.append("--particles not specified")
        elif not Path(self.args.particles).is_file():
            errors.append(f"Particle file not found: {self.args.particles}")
        else:
            self.log(f"✓ Particle file: {self.args.particles}")
        
        # Check passthrough file
        if self.args.passthrough:
            if not Path(self.args.passthrough).is_file():
                errors.append(f"Passthrough file not found: {self.args.passthrough}")
            else:
                self.log(f"✓ Passthrough file: {self.args.passthrough}")
        else:
            self.log("⚠ Passthrough file not specified (coordinates may be lost)", "WARNING")
        
        # Check output directory
        output_dir = Path(self.args.output).parent
        if output_dir.name == '':
            output_dir = Path('.')
        
        if not output_dir.is_dir():
            errors.append(f"Output directory not found: {output_dir}")
        else:
            self.log(f"✓ Output directory: {output_dir}")
        
        # Check micrograph path
        if self.args.micrograph_path:
            if not Path(self.args.micrograph_path).is_dir():
                self.log(f"⚠ Micrograph path doesn't exist yet: {self.args.micrograph_path}", "WARNING")
            else:
                self.log(f"✓ Micrograph path: {self.args.micrograph_path}")
        
        # Check original star
        if self.args.copy_coordinates and self.args.original_star:
            if not Path(self.args.original_star).is_file():
                errors.append(f"Original star file not found: {self.args.original_star}")
            else:
                self.log(f"✓ Original star file: {self.args.original_star}")
        
        if errors:
            for error in errors:
                self.log(f"✗ {error}", "ERROR")
            return False
        
        self.log("All validations passed!", "SUCCESS")
        return True
    
    def show_preview(self):
        """Show what will be done."""
        self.log("=" * 60, "INFO")
        self.log("PREVIEW", "INFO")
        self.log("=" * 60, "INFO")
        
        output_path = Path(self.args.output)
        self.log(f"Output star file: {output_path}")
        
        # Show csparc2star command
        cmd = ["csparc2star.py"]
        if self.args.inverty:
            cmd.append("--inverty")
        if self.args.strip_uid:
            cmd.append("--strip-uid=21")
        if self.args.micrograph_path:
            cmd.extend(["--micrograph-path", self.args.micrograph_path])
        
        cmd.append(self.args.particles)
        if self.args.passthrough:
            cmd.append(self.args.passthrough)
        cmd.append(str(output_path))
        
        self.log(f"Command: {' '.join(cmd)}")
        
        if self.args.copy_stacks:
            self.log("Will copy particle stacks to output directory")
            if self.args.rename_mrcs:
                self.log("  Will rename .mrc to .mrcs")
            if self.args.symlink:
                self.log("  Will create symlinks instead of copying")
        
        if self.args.copy_coordinates and self.args.original_star:
            self.log("Will merge coordinates from original star")
        
        self.log("Preview complete")
    
    def convert(self):
        """Execute the conversion."""
        self.log("=" * 60, "INFO")
        self.log("EXECUTION START", "INFO")
        self.log("=" * 60, "INFO")
        
        output_path = Path(self.args.output)
        output_dir = output_path.parent
        
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file
        if output_path.exists():
            backup_path = output_path.with_suffix(
                f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            )
            shutil.copy2(output_path, backup_path)
            self.log(f"Backed up existing file to: {backup_path}")
        
        # Step 1: Convert with csparc2star.py
        self.log("Step 1: Converting with csparc2star.py...", "INFO")
        
        cmd = ["csparc2star.py"]
        if self.args.inverty:
            cmd.append("--inverty")
        if self.args.strip_uid:
            cmd.append("--strip-uid=21")
        if self.args.micrograph_path:
            cmd.extend(["--micrograph-path", self.args.micrograph_path])
        
        cmd.extend([
            self.args.particles,
            self.args.passthrough if self.args.passthrough else "",
            str(output_path)
        ])
        cmd = [c for c in cmd if c]  # Remove empty strings
        
        self.log(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(output_dir),
                check=False
            )
            
            if result.returncode != 0:
                self.log(f"Error: {result.stderr}", "ERROR")
                return False
            
            self.log("✓ STAR file created successfully", "SUCCESS")
            if result.stdout:
                self.log(result.stdout)
        
        except FileNotFoundError:
            self.log("csparc2star.py not found. Install pyem with:", "ERROR")
            self.log("  conda install -c conda-forge pyem")
            return False
        except Exception as e:
            self.log(f"Execution failed: {str(e)}", "ERROR")
            return False
        
        # Step 2: Handle particle stacks
        if self.args.copy_stacks:
            self.log("Step 2: Handling particle stacks...", "INFO")
            if not self._handle_stacks(output_dir, output_path):
                self.log("Warning: Could not handle stacks", "WARNING")
        
        # Step 3: Merge coordinates
        if self.args.copy_coordinates and self.args.original_star:
            self.log("Step 3: Merging original coordinates...", "INFO")
            if not self._merge_coordinates(output_path):
                self.log("Warning: Could not merge coordinates", "WARNING")
        
        # Summary
        self.log("=" * 60, "INFO")
        self.log("CONVERSION COMPLETE", "SUCCESS")
        self.log("=" * 60, "INFO")
        self.log(f"Output star file: {output_path}")
        self.log(f"Output directory: {output_dir}")
        
        # Next steps
        self.log("\nNEXT STEPS:", "INFO")
        self.log(f"1. Test reconstruction:")
        self.log(f"   cd {output_dir}")
        self.log(f"   relion_reconstruct --i {output_path.name} --o test_map.mrc")
        self.log(f"\n2. Import into RELION:")
        self.log(f"   RELION GUI → Import → Particles → {output_path.name}")
        
        return True
    
    def _handle_stacks(self, output_dir, output_star):
        """Copy/symlink particle stacks, preserving cryoSPARC directory hierarchy (e.g., J67/extract/)."""
        try:
            import re
            with open(output_star) as f:
                content = f.read()

            # Match image refs like "000003@J67/extract/file.mrc" - capture prefix and path separately
            raw_refs = re.findall(r'(\d+@)?(\S+\.mr[cs]+)', content)
            # raw_refs is list of tuples: (prefix_or_empty, path)
            stack_paths = [p for (prefix, p) in raw_refs if '/' in p]
            if not stack_paths:
                self.log("No particle stack references found", "WARNING")
                return False

            first_path = stack_paths[0]
            ref_path = Path(first_path)
            # ref_path.parent is e.g. "J67/extract"

            # CryoSPARC project root = parent of the job folder containing particles.cs
            particle_file = Path(self.args.particles)
            cs_project_root = particle_file.parent.parent  # J82 -> project root

            # Full source path on disk
            source_dir = cs_project_root / ref_path.parent
            if not source_dir.exists():
                self.log(f"Stack directory not found: {source_dir}", "WARNING")
                return False

            # Target: PRESERVE cryoSPARC hierarchy (e.g., output_dir/J67/extract)
            target_dir = output_dir / ref_path.parent
            self.log(f"Auto-detected source: {source_dir}", "INFO")
            self.log(f"Target (preserving cryoSPARC hierarchy): {target_dir}", "INFO")

            if target_dir.exists():
                if target_dir.is_symlink():
                    target_dir.unlink()
                else:
                    shutil.rmtree(target_dir)

            # Ensure parent directory exists (e.g., output_dir/J67/)
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            if self.args.symlink:
                os.symlink(source_dir, target_dir)
                self.log(f"✓ Created symlink: {target_dir}", "SUCCESS")
            else:
                shutil.copytree(source_dir, target_dir)
                self.log(f"✓ Copied stacks to: {target_dir}", "SUCCESS")

            # Rename .mrc -> .mrcs on disk (RELION convention)
            if self.args.rename_mrcs:
                count = 0
                for mrc_file in target_dir.glob("*.mrc"):
                    mrc_file.rename(mrc_file.with_suffix(".mrcs"))
                    count += 1
                if count:
                    self.log(f"✓ Renamed {count} .mrc -> .mrcs on disk", "SUCCESS")

            # Rewrite paths in star file: rename .mrc -> .mrcs ONLY
            # CRITICAL: DO NOT strip the NNNNNN@ prefix - it's essential RELION syntax!
            new_content = content
            if self.args.rename_mrcs:
                new_content = re.sub(r'\.mrc(?!s)', '.mrcs', new_content)

            with open(output_star, 'w') as f:
                f.write(new_content)
            self.log(f"✓ Updated star file extensions (.mrc -> .mrcs)", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Error handling stacks: {str(e)}", "ERROR")
            return False

    def _merge_coordinates(self, output_star):
        """Merge coordinates from original star."""
        try:
            cmd = [
                "star.py",
                "--copy-micrograph-coordinates",
                self.args.original_star,
                str(output_star),
                str(output_star)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.log(f"Error merging: {result.stderr}", "WARNING")
                return False
            
            self.log("✓ Coordinates merged", "SUCCESS")
            return True
        
        except FileNotFoundError:
            self.log("star.py not found (part of pyem)", "WARNING")
            return False
        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Convert cryoSPARC particles to RELION format",
        epilog="""
Examples:
  %(prog)s --particles particles.cs --passthrough pass.cs --output out.star
  %(prog)s --particles particles.cs --output out.star --inverty --strip-uid
  %(prog)s --particles particles.cs --output out.star --preview
  %(prog)s --particles particles.cs --output out.star --copy-stacks --symlink
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--particles", "-p",
        required=True,
        help="CryoSPARC particle .cs file (required)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--passthrough",
        help="CryoSPARC passthrough .cs file (contains coordinates)"
    )
    parser.add_argument(
        "--output", "-o",
        default="particles_relion.star",
        help="Output RELION star filename (default: particles_relion.star)"
    )
    parser.add_argument(
        "--original-star",
        help="Original RELION star (for merging coordinates)"
    )
    
    # Flags
    parser.add_argument(
        "--inverty",
        action="store_true",
        help="Invert Y-axis (use if from MotionCor2/RELION)"
    )
    parser.add_argument(
        "--strip-uid",
        action="store_true",
        default=True,
        help="Remove CryoSPARC UID prefix (default: True)"
    )
    parser.add_argument(
        "--no-strip-uid",
        action="store_false",
        dest="strip_uid",
        help="Keep UID prefix"
    )
    parser.add_argument(
        "--micrograph-path",
        help="Directory path to prepend to micrograph names"
    )
    
    # Stack options
    parser.add_argument(
        "--copy-stacks",
        action="store_true",
        default=True,
        help="Copy particle stacks (default: True)"
    )
    parser.add_argument(
        "--no-copy-stacks",
        action="store_false",
        dest="copy_stacks",
        help="Don't copy stacks"
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Use symlinks instead of copying stacks"
    )
    parser.add_argument(
        "--rename-mrcs",
        action="store_true",
        default=True,
        help="Rename .mrc to .mrcs (default: True)"
    )
    parser.add_argument(
        "--no-rename-mrcs",
        action="store_false",
        dest="rename_mrcs",
        help="Don't rename stacks"
    )
    
    # Coordinate merging
    parser.add_argument(
        "--copy-coordinates",
        action="store_true",
        help="Merge coordinates from original star"
    )
    
    # Execution options
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate inputs and exit"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show preview and exit (don't execute)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Don't ask for confirmation"
    )
    
    # Logging
    parser.add_argument(
        "--log-file",
        help="Write detailed log to file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = Cryo2RelionCLI(args)
    
    # Validate inputs
    if not cli.validate_inputs():
        sys.exit(1)
    
    # Show preview
    if args.preview:
        cli.show_preview()
        sys.exit(0)
    
    # Only validate
    if args.validate:
        sys.exit(0)
    
    # Ask for confirmation (unless forced)
    if not args.force:
        response = input("\nExecute conversion? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    # Execute
    success = cli.convert()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
