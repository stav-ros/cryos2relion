# CryoSPARC → RELION Particle Export Tool
## Installation & Quick-Start Guide

### Prerequisites
- Python 3.7+
- Conda (recommended) or pip
- Access to cryoSPARC output files (.cs)
- RELION 5 (for final import)

### Installation

#### Option 1: Conda (Recommended)
```bash
# Create a dedicated environment
conda create -n cryo2relion python=3.10
conda activate cryo2relion

# Install required packages
conda install -c conda-forge pyem pandas starfile

# Clone/download the tool
# (Place cryo2relion_gui.py in your working directory)
```

#### Option 2: Pip
```bash
pip install --upgrade pip
pip install pyem pandas starfile

# Or install from GitHub
pip install git+https://github.com/asarnow/pyem.git
```

---

## Running the GUI

### Quick Start
```bash
cd /path/to/your/relion/project
python cryo2relion_gui.py
```

A window will open with tabs for:
1. **Select Files** - Choose your cryoSPARC outputs
2. **Options** - Configure conversion parameters
3. **Execute & Log** - Run conversion and view results
4. **Help** - Detailed documentation

### What You Need
From cryoSPARC, download from your refinement job:
- ✓ **particles.cs** (or `cryosparc_Px_Jy_particles.cs`)
- ✓ **passthrough file** (e.g., `Px_Jy_passthrough_particles.cs`) - **ESSENTIAL for coordinates**

In cryoSPARC GUI:
```
Job → Output → "Download Particle Alignments" (for refinement)
      or "Download Particle Stack" (for 2D/3D class)
```

---

## Command-Line Usage (Advanced)

For scripting or HPC cluster submissions:

```bash
# Basic conversion
csparc2star.py particles.cs passthrough_particles.cs output.star

# With common options
csparc2star.py \
  --inverty \
  --strip-uid \
  --micrograph-path /path/to/Micrographs/ \
  particles.cs passthrough_particles.cs output.star

# Merge original coordinates
star.py --copy-micrograph-coordinates original.star \
  output.star output_final.star
```

---

## Workflow Example

### In the GUI:

1. **Tab 1: Select Files**
   - Click "Browse" → select `particles.cs`
   - Click "Browse" → select `passthrough_particles.cs`
   - Select output directory (e.g., `/data/myproject/`)
   - Filename: `particles_relion.star`

2. **Tab 2: Options**
   - Check "✓ --inverty" (if from MotionCor2/RELION)
   - Check "✓ --strip-uid" (recommended for clean filenames)
   - Check "✓ Copy particle stacks"
   - Check "✓ Rename .mrc to .mrcs"

3. **Tab 3: Execute**
   - Click "Validate Inputs" → should show ✓ checks
   - Click "Preview Conversion" → see what will happen
   - Click "▶ EXECUTE CONVERSION" → run it
   - Wait for completion message

4. **Verify**
   ```bash
   cd /data/myproject/
   relion_reconstruct --i particles_relion.star --o test_map.mrc
   ```

---

## Common Scenarios

### Scenario 1: Re-extract in RELION
```
Use case: You want to re-extract particles at different binning

1. Convert cryoSPARC to RELION star (this tool)
2. RELION: Import → Particles → particles_relion.star
3. RELION: Preprocess → Extract → (adjust bin/size/center)
4. Continue with 2D/3D classification
```

### Scenario 2: 3D Reconstruction from cryoSPARC
```
Use case: Verify angles transferred correctly

1. Convert with this tool (preserves Euler angles)
2. Run: relion_reconstruct --i particles_relion.star --o map.mrc
3. Compare map.mrc with your cryoSPARC reconstruction
   → Should be identical
```

### Scenario 3: Import into RELION with original coordinates
```
Use case: Particles were originally in RELION, modified in cryoSPARC

1. Tab 1: Specify "Original RELION STAR" file
2. Tab 2: Check "Use original coordinates"
3. This restores exact micrograph positions from RELION
```

---

## Validation & Safety Features

The tool includes automatic checks:

✓ **File validation**
  - Checks all files exist and are readable
  - Validates .cs and .star file formats
  - Warns if passthrough is missing

✓ **Path validation**
  - Ensures relative paths work correctly
  - Checks particle coords fit within micrographs
  - Verifies stack files are accessible

✓ **Backups**
  - Automatically backs up existing output files
  - Saves with timestamp: `particles_relion.2024.01.15.bak`

✓ **Error handling**
  - Clear error messages with solutions
  - Logs all operations for debugging
  - Suggests fixes for common issues

---

## Troubleshooting

### "PyEM not found" Error
```bash
conda install -c conda-forge pyem
# OR
pip install git+https://github.com/asarnow/pyem.git
```

### "Passthrough file not found"
cryoSPARC should generate this automatically. If missing:
- Check Job → Output → you should see multiple .cs files
- Look for files with "passthrough" in the name
- Download both particle file AND passthrough file

### "relion_reconstruct" fails with "Cannot find image"
1. Check star file paths:
   ```bash
   head -50 particles_relion.star | grep _rlnImageName
   ```
2. Verify .mrcs files exist:
   ```bash
   ls -la extract/*.mrcs
   ```
3. Check relative paths are correct:
   ```bash
   cd /path/to/relion/project
   cat particles_relion.star | grep extract
   ```

### Stars don't match between cryoSPARC and RELION
- Add `--inverty` flag if particles came from MotionCor2
- Use original star merging if coordinates are critical
- Check that micrograph paths are identical

### UID prefixes not removed
If filenames still have `000000000000123456789_particle001.mrcs`:
- Use `--strip-uid` flag (checked by default in GUI)
- Or manually in star file:
  ```bash
  sed -i 's/[0-9]\{21\}_//g' particles_relion.star
  ```

---

## Advanced Configuration

### Custom Environment Variables
```bash
# Set number of cores for PyEM
export NUMEXPR_MAX_THREADS=8
python cryo2relion_gui.py
```

### Using Different PyEM Version
```bash
# Install specific pyem version
pip install git+https://github.com/asarnow/pyem.git@v0.67

# Check version
python -c "import pyem; print(pyem.__version__)"
```

### Batch Processing
```bash
# Process multiple jobs (shell script)
for job_dir in cryosparc2_master/project/P*/J*/; do
    particles="${job_dir}/cryosparc_P*_J*_particles.cs"
    passthrough="${job_dir}/P*_J*_passthrough_particles.cs"
    
    csparc2star.py --strip-uid --inverty \
        "$particles" "$passthrough" \
        "$(basename $job_dir)_particles.star"
done
```

---

## References

- **PyEM GitHub**: https://github.com/asarnow/pyem
- **PyEM Wiki**: https://github.com/asarnow/pyem/wiki
- **CryoSPARC Export Guide**: https://discuss.cryosparc.com/t/exporting-coordinates-of-picked-particles/2154
- **RELION Manual**: https://relion.readthedocs.io/

---

## Performance Tips

For large datasets:

1. **Use symlinks instead of copying**
   - Tab 2: Check "Create symlinks instead"
   - Saves disk space (~50% reduction)

2. **Process on HPC with batch scripts**
   ```bash
   #!/bin/bash
   #SBATCH --time=00:10:00
   #SBATCH --mem=4G
   
   cd /scratch/project
   csparc2star.py --strip-uid --inverty \
       particles.cs passthrough.cs particles.star
   ```

3. **Parallel jobs**
   - Separate cryoSPARC jobs can be converted in parallel
   - No resource conflicts between conversions

---

## Citation

If you use this tool in published work:

- **PyEM**: Asarnow et al. (2019) https://github.com/asarnow/pyem
- **CryoSPARC**: Punjani et al., Nature Methods (2017)
- **RELION**: Zivanov et al., eLife (2018)

---

## Support

For issues:
1. Check the Help tab in the GUI
2. Review the log output for specific errors
3. See troubleshooting section above
4. Visit: https://github.com/asarnow/pyem/issues

Questions about cryoSPARC export:
- https://discuss.cryosparc.com/ (CryoSPARC community)
- Look for "export to relion" threads

---

**Last Updated**: 2024
**Tested with**: PyEM 0.66+, CryoSPARC 4.5+, RELION 5.0+
