# EnclosureAI — Module Library Validation Script
# Runs openscad --render on test instantiations of every module.
# Reports pass/fail per module. Exits non-zero if any module fails.

$ErrorActionPreference = "Continue"
$script_dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$module_dir = Join-Path $script_dir "app\scad\module_library"

# Check OpenSCAD availability
$openscad = Get-Command "openscad" -ErrorAction SilentlyContinue
if (-not $openscad) {
    $openscad_paths = @(
        "C:\Program Files\OpenSCAD\openscad.exe",
        "C:\Program Files (x86)\OpenSCAD\openscad.exe"
    )
    foreach ($path in $openscad_paths) {
        if (Test-Path $path) {
            $openscad = $path
            break
        }
    }
}

if (-not $openscad) {
    Write-Host "WARNING: OpenSCAD not found in PATH. Skipping render validation." -ForegroundColor Yellow
    Write-Host "Module files will be checked for existence only."
    
    $all_modules = Get-ChildItem -Path $module_dir -Recurse -Filter "*.scad"
    $count = $all_modules.Count
    Write-Host "`nFound $count .scad module files:" -ForegroundColor Cyan
    foreach ($f in $all_modules) {
        $rel = $f.FullName.Substring($module_dir.Length + 1)
        Write-Host "  [EXISTS] $rel" -ForegroundColor Green
    }
    Write-Host "`nAll $count module files exist. Render validation skipped (no OpenSCAD)." -ForegroundColor Yellow
    exit 0
}

Write-Host "OpenSCAD found: $openscad" -ForegroundColor Green
Write-Host ""

# Test instantiations for each module
$tests = @(
    @{
        Name = "common/standoff"
        File = "common\standoff.scad"
        Code = 'use <common/standoff.scad>; standoff(6.4, 3.2, 5);'
    },
    @{
        Name = "common/screw_boss"
        File = "common\screw_boss.scad"
        Code = 'use <common/screw_boss.scad>; screw_boss(8, 3.2, 10);'
    },
    @{
        Name = "common/snap_fit"
        File = "common\snap_fit.scad"
        Code = 'use <common/snap_fit.scad>; snap_fit_tab(6, 3, 1.2, 0.8, 0.3);'
    },
    @{
        Name = "common/vent_slots"
        File = "common\vent_slots.scad"
        Code = 'use <common/vent_slots.scad>; vent_slots(4, 2.5, 15, 4, 1.2);'
    },
    @{
        Name = "common/pcb_groove"
        File = "common\pcb_groove.scad"
        Code = 'use <common/pcb_groove.scad>; pcb_groove(50, 1.5, 2.0, 5);'
    },
    @{
        Name = "rectangular_flat/body"
        File = "strategies\rectangular_flat\body.scad"
        Code = 'use <strategies/rectangular_flat/body.scad>; rectangular_body(60, 40, 15, 1.2);'
    },
    @{
        Name = "rectangular_flat/lid"
        File = "strategies\rectangular_flat\lid.scad"
        Code = 'use <strategies/rectangular_flat/lid.scad>; rectangular_lid(60, 40, 1.5);'
    },
    @{
        Name = "clamshell_horizontal/lower_shell"
        File = "strategies\clamshell_horizontal\lower_shell.scad"
        Code = 'use <strategies/clamshell_horizontal/lower_shell.scad>; clamshell_lower_shell(60, 40, 10, 1.2, 6.2, 1.5, 2.0, 30, 0);'
    },
    @{
        Name = "clamshell_horizontal/upper_shell"
        File = "strategies\clamshell_horizontal\upper_shell.scad"
        Code = 'use <strategies/clamshell_horizontal/upper_shell.scad>; clamshell_upper_shell(60, 40, 10, 1.2, 30, 10);'
    },
    @{
        Name = "chimney_thermal/base_body"
        File = "strategies\chimney_thermal\base_body.scad"
        Code = 'use <strategies/chimney_thermal/base_body.scad>; chimney_base_body(80, 60, 20, 1.2, 40, 30, 20, 20, 3.2);'
    },
    @{
        Name = "chimney_thermal/chimney_stack"
        File = "strategies\chimney_thermal\chimney_stack.scad"
        Code = 'use <strategies/chimney_thermal/chimney_stack.scad>; chimney_stack(20, 20, 30, 1.2);'
    },
    @{
        Name = "chimney_thermal/lid"
        File = "strategies\chimney_thermal\lid.scad"
        Code = 'use <strategies/chimney_thermal/lid.scad>; chimney_lid(80, 60, 1.5, 40, 30, 20, 20);'
    },
    @{
        Name = "din_rail_clip/body"
        File = "strategies\din_rail_clip\body.scad"
        Code = 'use <strategies/din_rail_clip/body.scad>; din_rail_body(80, 50, 25, 1.5);'
    },
    @{
        Name = "din_rail_clip/din_clip"
        File = "strategies\din_rail_clip\din_clip.scad"
        Code = 'use <strategies/din_rail_clip/din_clip.scad>; din_rail_clip(35.0, 5.5, 14.0, 8.0, 50);'
    },
    @{
        Name = "din_rail_clip/lid"
        File = "strategies\din_rail_clip\lid.scad"
        Code = 'use <strategies/din_rail_clip/lid.scad>; din_rail_lid(80, 50, 1.5, 3.2, 5);'
    },
    @{
        Name = "wearable_rounded/lower_shell"
        File = "strategies\wearable_rounded\lower_shell.scad"
        Code = 'use <strategies/wearable_rounded/lower_shell.scad>; wearable_lower_shell(40, 30, 8, 1.0, 5, 2);'
    },
    @{
        Name = "wearable_rounded/upper_shell"
        File = "strategies\wearable_rounded\upper_shell.scad"
        Code = 'use <strategies/wearable_rounded/upper_shell.scad>; wearable_upper_shell(40, 30, 8, 1.0, 5, 2);'
    },
    @{
        Name = "wearable_rounded/band_lug"
        File = "strategies\wearable_rounded\band_lug.scad"
        Code = 'use <strategies/wearable_rounded/band_lug.scad>; band_lug(8, 4, 3, 6, 2);'
    }
)

$passed = 0
$failed = 0
$total = $tests.Count
$temp_dir = Join-Path $script_dir "temp_validation"
New-Item -ItemType Directory -Path $temp_dir -Force | Out-Null

Set-Location $module_dir

foreach ($test in $tests) {
    $test_file = Join-Path $temp_dir "test_$($test.Name -replace '/', '_').scad"
    $stl_file = Join-Path $temp_dir "test_$($test.Name -replace '/', '_').stl"
    
    # Write test file without BOM
    [System.IO.File]::WriteAllText($test_file, $test.Code)
    
    # Check module file exists
    $module_path = Join-Path $module_dir $test.File
    if (-not (Test-Path $module_path)) {
        Write-Host "  [FAIL] $($test.Name) - module file not found" -ForegroundColor Red
        $failed++
        continue
    }
    
    # Run openscad
    try {
        $stderr_file = Join-Path $temp_dir "stderr.txt"
        & $openscad --render -o $stl_file $test_file 2> $stderr_file
        if ($LASTEXITCODE -eq 0 -and (Test-Path $stl_file)) {
            Write-Host "  [PASS] $($test.Name)" -ForegroundColor Green
            $passed++
        } else {
            $stderr = Get-Content $stderr_file -Raw -ErrorAction SilentlyContinue
            Write-Host "  [FAIL] $($test.Name) - exit code $LASTEXITCODE" -ForegroundColor Red
            if ($stderr) { Write-Host "         $($stderr.Substring(0, [Math]::Min(200, $stderr.Length)))" -ForegroundColor DarkRed }
            $failed++
        }
    } catch {
        Write-Host "  [FAIL] $($test.Name) - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

# Cleanup
Remove-Item -Path $temp_dir -Recurse -Force -ErrorAction SilentlyContinue

# Summary
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Module Validation Results" -ForegroundColor Cyan
Write-Host "  Passed: $passed / $total" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "  Failed: $failed / $total" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "===========================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
