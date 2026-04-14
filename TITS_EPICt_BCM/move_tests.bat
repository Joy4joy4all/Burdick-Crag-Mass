@echo off
REM ═══════════════════════════════════════════════════════════
REM  Move all BCM test scripts to EPIC test folder
REM  Run from: Burdick_Crag_Mass_Substrate_Solver\ (repo root)
REM ═══════════════════════════════════════════════════════════
echo.
echo  MOVING TEST SCRIPTS TO EPIC TEST FOLDER
echo  ════════════════════════════════════════
echo.

set DEST=TITS_EPICt_BCM\BCM_EPIC_OpT_tests

if not exist "%DEST%" (
    mkdir "%DEST%"
    echo   CREATED: %DEST%
)

REM ── v7-v14 Foundation Tests ──
for %%f in (test_crag_calibration.py test_edge_coupling.py test_observables.py BCM_v14_kill_tests.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v15 External Frame ──
for %%f in (BCM_v15_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v16 TITS Probes ──
for %%f in (BCM_v16_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v17 Frequency & Brucetron ──
for %%f in (BCM_v17_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v18 Frastrate & Phase ──
for %%f in (BCM_v18_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v19 Chi Operator & Corridor ──
for %%f in (BCM_v19_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v20 Stellar & BH Transit ──
for %%f in (BCM_v20_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v21 Arrival & Gate ──
for %%f in (BCM_v21_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v22 Reverse Engine & Chi-Squared ──
for %%f in (BCM_v22_*.py BCM_chi_squared_engine.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── v23 Neutrino Flux ──
for %%f in (BCM_v23_*.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── EPIC deck builder ──
for %%f in (BCM_EPIC_OpT_test_deck.py) do (
    if exist "%%f" (
        move "%%f" "%DEST%\%%f" >nul
        echo   MOVED: %%f
    )
)

REM ── Count ──
echo.
set /a count=0
for %%f in ("%DEST%\*.py") do set /a count+=1
echo  TOTAL: %count% test scripts moved to %DEST%
echo.
echo  DONE. Now update launcher.py TEST_REGISTRY path.
pause
