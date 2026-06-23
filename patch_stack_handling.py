#!/usr/bin/env python3
"""Patch both GUI and CLI scripts to correctly auto-detect and rewrite stack paths."""
import re
from pathlib import Path

NEW_METHOD_GUI = '''    def _handle_particle_stacks(self, output_dir, output_star):
        """Copy/symlink particle stacks, auto-detecting source from star file and rewriting paths."""
        try:
            import re
            with open(output_star) as f:
                content = f.read()

            # Find first stack reference in star file (e.g., "J67/extract/file.mrcs")
            stack_refs = re.findall(r'\\S+\\.mr[cs]+', content)
            stack_refs = [r for r in stack_refs if '/' in r]
            if not stack_refs:
                self._log("No particle stack references found in star file", "WARNING")
                return False

            first_ref = stack_refs[0]
            ref_path = Path(first_ref)
            # ref_path.parent is e.g. "J67/extract"

            # CryoSPARC project root = parent of the job folder containing particles.cs
            particle_file = Path(self.particle_file.get())
            cs_project_root = particle_file.parent.parent  # J82 -> project root

            # Full source path on disk
            source_dir = cs_project_root / ref_path.parent
            if not source_dir.exists():
                self._log(f"Stack directory not found: {source_dir}", "WARNING")
                return False

            # Target: output_dir/extract (flattened)
            target_dir = output_dir / "extract"
            self._log(f"Auto-detected source: {source_dir}", "INFO")
            self._log(f"Target: {target_dir}", "INFO")

            if target_dir.exists():
                if target_dir.is_symlink():
                    target_dir.unlink()
                else:
                    shutil.rmtree(target_dir)

            if self.create_symlinks.get():
                os.symlink(source_dir, target_dir)
                self._log("✓ Created symlink", "SUCCESS")
            else:
                shutil.copytree(source_dir, target_dir)
                self._log("✓ Copied stacks", "SUCCESS")

            # Rename .mrc -> .mrcs on disk
            if self.rename_mrcs.get():
                count = 0
                for mrc_file in target_dir.glob("*.mrc"):
                    mrc_file.rename(mrc_file.with_suffix(".mrcs"))
                    count += 1
                if count:
                    self._log(f"✓ Renamed {count} .mrc -> .mrcs", "SUCCESS")

            # CRITICAL: rewrite paths inside the star file
            old_prefix = str(ref_path.parent) + "/"   # e.g. "J67/extract/"
            new_prefix = "extract/"
            new_content = content.replace(old_prefix, new_prefix)
            if self.rename_mrcs.get():
                new_content = new_content.replace(".mrc", ".mrcs")
            with open(output_star, 'w') as f:
                f.write(new_content)
            self._log(f"✓ Rewrote star paths: {old_prefix} -> {new_prefix}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"Error handling stacks: {str(e)}", "ERROR")
            return False'''

NEW_METHOD_CLI = '''    def _handle_stacks(self, output_dir, output_star):
        """Copy/symlink particle stacks, auto-detecting source from star file and rewriting paths."""
        try:
            import re
            with open(output_star) as f:
                content = f.read()

            stack_refs = re.findall(r'\\S+\\.mr[cs]+', content)
            stack_refs = [r for r in stack_refs if '/' in r]
            if not stack_refs:
                self.log("No particle stack references found", "WARNING")
                return False

            first_ref = stack_refs[0]
            ref_path = Path(first_ref)

            particle_file = Path(self.args.particles)
            cs_project_root = particle_file.parent.parent

            source_dir = cs_project_root / ref_path.parent
            if not source_dir.exists():
                self.log(f"Stack directory not found: {source_dir}", "WARNING")
                return False

            target_dir = output_dir / "extract"
            self.log(f"Auto-detected source: {source_dir}")
            self.log(f"Target: {target_dir}")

            if target_dir.exists():
                if target_dir.is_symlink():
                    target_dir.unlink()
                else:
                    shutil.rmtree(target_dir)

            if self.args.symlink:
                os.symlink(source_dir, target_dir)
                self.log("✓ Created symlink", "SUCCESS")
            else:
                shutil.copytree(source_dir, target_dir)
                self.log("✓ Copied stacks", "SUCCESS")

            if self.args.rename_mrcs:
                count = 0
                for mrc_file in target_dir.glob("*.mrc"):
                    mrc_file.rename(mrc_file.with_suffix(".mrcs"))
                    count += 1
                if count:
                    self.log(f"✓ Renamed {count} .mrc -> .mrcs", "SUCCESS")

            old_prefix = str(ref_path.parent) + "/"
            new_prefix = "extract/"
            new_content = content.replace(old_prefix, new_prefix)
            if self.args.rename_mrcs:
                new_content = new_content.replace(".mrc", ".mrcs")
            with open(output_star, 'w') as f:
                f.write(new_content)
            self.log(f"✓ Rewrote star paths: {old_prefix} -> {new_prefix}", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Error handling stacks: {str(e)}", "ERROR")
            return False'''

def patch_file(path, pattern_start, pattern_end, new_method):
    text = path.read_text()
    # Find the method by its def line and replace until the next method at same indent
    start_match = re.search(pattern_start, text)
    if not start_match:
        print(f"  ✗ Could not find method start in {path}")
        return False
    start_idx = start_match.start()
    # Find end: next "    def " at same indent level after the start
    rest = text[start_match.end():]
    end_match = re.search(r'\n    def ', rest)
    if end_match:
        end_idx = start_match.end() + end_match.start()
    else:
        end_idx = len(text)
    new_text = text[:start_idx] + new_method + "\n\n" + text[end_idx:]
    path.write_text(new_text)
    print(f"  ✓ Patched {path}")
    return True

for f in Path('.').glob('cryo2relion_gui.py'):
    patch_file(f, r'    def _handle_particle_stacks\(self', r'', NEW_METHOD_GUI)
for f in Path('.').glob('cryo2relion_cli.py'):
    patch_file(f, r'    def _handle_stacks\(self', r'', NEW_METHOD_CLI)
print("Done.")
