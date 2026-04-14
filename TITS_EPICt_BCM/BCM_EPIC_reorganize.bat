@echo off
REM ═══════════════════════════════════════════════════════════
REM  BCM EPIC — Directory Reorganization Script
REM  Stephen Justin Burdick Sr. — Emerald Entities LLC
REM  Run from: TITS_EPICt_BCM/
REM ═══════════════════════════════════════════════════════════
echo.
echo  BCM EPIC — REORGANIZATION
echo  ═══════════════════════════
echo.

REM ── Verify we're in the right directory ──
if not exist "genesis_brain" (
    echo ERROR: Run this from TITS_EPICt_BCM directory
    echo   cd C:\TITS\TITS_GIBUSH_AISOS_SPINE\Burdick_Crag_Mass_Substrate_Solver\TITS_EPICt_BCM
    pause
    exit /b 1
)

echo  Step 1: Delete old/duplicate files
echo  ───────────────────────────────────

REM Files marked DELETE in the audit
if exist "genesis_cognitive_engine.py" (
    del "genesis_cognitive_engine.py"
    echo   DELETED: genesis_cognitive_engine.py (duplicate)
)
if exist "generate_interview_db.py" (
    del "generate_interview_db.py"
    echo   DELETED: generate_interview_db.py (hardcoded people)
)
if exist "genesis_brain\GENESIS_BRAIN_FULL_AUDIT.md" (
    del "genesis_brain\GENESIS_BRAIN_FULL_AUDIT.md"
    echo   DELETED: GENESIS_BRAIN_FULL_AUDIT.md (old audit)
)
if exist "genesis_brain\genesis_cognitive_engine.py" (
    del "genesis_brain\genesis_cognitive_engine.py"
    echo   DELETED: genesis_brain\genesis_cognitive_engine.py (duplicate)
)

REM Old doctoral_interviewer at root (duplicate of genesis_brain version)
if exist "doctoral_interviewer.py" (
    del "doctoral_interviewer.py"
    echo   DELETED: doctoral_interviewer.py (root duplicate)
)

echo.
echo  Step 2: Rename files with old terminology
echo  ──────────────────────────────────────────

REM Root level renames
if exist "interview_intelligence.py" (
    if not exist "test_intelligence.py" (
        ren "interview_intelligence.py" "test_intelligence.py"
        echo   RENAMED: interview_intelligence.py → test_intelligence.py
    ) else (
        del "interview_intelligence.py"
        echo   DELETED: interview_intelligence.py (converted version exists)
    )
)
if exist "interview_reconciler.py" (
    if not exist "test_reconciler.py" (
        ren "interview_reconciler.py" "test_reconciler.py"
        echo   RENAMED: interview_reconciler.py → test_reconciler.py
    ) else (
        del "interview_reconciler.py"
        echo   DELETED: interview_reconciler.py (converted version exists)
    )
)
if exist "post_interview_generator.py" (
    if not exist "post_test_generator.py" (
        ren "post_interview_generator.py" "post_test_generator.py"
        echo   RENAMED: post_interview_generator.py → post_test_generator.py
    ) else (
        del "post_interview_generator.py"
        echo   DELETED: post_interview_generator.py (converted version exists)
    )
)
if exist "progressive_interview_engine.py" (
    if not exist "progressive_test_engine.py" (
        ren "progressive_interview_engine.py" "progressive_test_engine.py"
        echo   RENAMED: progressive_interview_engine.py → progressive_test_engine.py
    ) else (
        del "progressive_interview_engine.py"
        echo   DELETED: progressive_interview_engine.py (converted version exists)
    )
)
if exist "test_fusion.py" (
    if not exist "test_bcm.py" (
        ren "test_fusion.py" "test_bcm.py"
        echo   RENAMED: test_fusion.py → test_bcm.py
    ) else (
        del "test_fusion.py"
        echo   DELETED: test_fusion.py (converted version exists)
    )
)
if exist "BCM_EPIC_OpT_interview_collector.py" (
    if not exist "BCM_EPIC_OpT_test_collector.py" (
        ren "BCM_EPIC_OpT_interview_collector.py" "BCM_EPIC_OpT_test_collector.py"
        echo   RENAMED: BCM_EPIC_OpT_interview_collector.py → BCM_EPIC_OpT_test_collector.py
    ) else (
        del "BCM_EPIC_OpT_interview_collector.py"
        echo   DELETED: BCM_EPIC_OpT_interview_collector.py (converted version exists)
    )
)
if exist "fusion_interview_collector.py" (
    del "fusion_interview_collector.py"
    echo   DELETED: fusion_interview_collector.py (old name)
)
if exist "bmc_engine.py" (
    if not exist "BCM_engine.py" (
        ren "bmc_engine.py" "BCM_engine.py"
        echo   RENAMED: bmc_engine.py → BCM_engine.py
    ) else (
        del "bmc_engine.py"
        echo   DELETED: bmc_engine.py (converted version exists)
    )
)

REM Old Excel interview plan
if exist "project_team_name_interview_xcel\GIBUSH_Fusion_Interview_Plan.xlsx" (
    echo   NOTE: Old interview Excel still at project_team_name_interview_xcel\
    echo         Replace with BCM_Test_Plan.xlsx when ready
)
if exist "project_team_name_interview_xcel\AISOS_SPINE_Fusion_Interview_Plan.xlsx" (
    del "project_team_name_interview_xcel\AISOS_SPINE_Fusion_Interview_Plan.xlsx"
    echo   DELETED: AISOS_SPINE interview plan (not needed)
)

echo.
echo  Step 3: Clean __pycache__
echo  ─────────────────────────

if exist "__pycache__" (
    rd /s /q "__pycache__"
    echo   CLEANED: __pycache__
)
if exist "genesis_brain\__pycache__" (
    rd /s /q "genesis_brain\__pycache__"
    echo   CLEANED: genesis_brain\__pycache__
)
if exist "Inclusion_Module_Receipt_Collector\__pycache__" (
    rd /s /q "Inclusion_Module_Receipt_Collector\__pycache__"
    echo   CLEANED: Inclusion_Module_Receipt_Collector\__pycache__
)

echo.
echo  Step 4: Clean GENESIS_OUTPUT (regenerate fresh)
echo  ────────────────────────────────────────────────

if exist "GENESIS_OUTPUT\interview_graph.json" (
    del "GENESIS_OUTPUT\interview_graph.json"
    echo   DELETED: old interview_graph.json
)
if exist "GENESIS_OUTPUT\New folder" (
    rd /s /q "GENESIS_OUTPUT\New folder"
    echo   DELETED: empty New folder
)

echo.
echo  Step 5: Rename analysis folder files
echo  ─────────────────────────────────────

if exist "BCM_EPIC_OpT_analysis" (
    echo   BCM_EPIC_OpT_analysis/ — old equipment impact reports
    echo   These are historical I-Corps data. Keep for reference.
)

echo.
echo  Step 6: Verify final structure
echo  ──────────────────────────────

echo.
echo  ROOT FILES:
for %%f in (*.py) do echo   %%f

echo.
echo  GENESIS_BRAIN:
for %%f in (genesis_brain\*.py) do echo   %%f

echo.
echo  CONFIG:
for %%f in (config\*.*) do echo   %%f

echo.
echo  BCM_NAVIGATOR_PROJECT:
dir /b /ad BCM_Navigator_Project 2>nul

echo.
echo  Step 7: Verify zero interview references
echo  ─────────────────────────────────────────

set /a total=0
for %%f in (*.py) do (
    findstr /i /c:"interview" "%%f" >nul 2>&1
    if not errorlevel 1 (
        echo   WARNING: %%f still contains "interview"
        set /a total+=1
    )
)
for %%f in (genesis_brain\*.py) do (
    findstr /i /c:"interview" "%%f" >nul 2>&1
    if not errorlevel 1 (
        echo   WARNING: %%f still contains "interview"
        set /a total+=1
    )
)

echo.
echo  ═══════════════════════════════════════
echo  REORGANIZATION COMPLETE
echo  ═══════════════════════════════════════
echo.
echo  Next: Drop converted .py files from Claude
echo  into their respective locations, then re-run
echo  this script to verify zero interview refs.
echo.
pause
