#!/usr/bin/env python3
"""
Acceptance test suite for TECNO KL5 Slot B Stock Package on Windows.
Runs under windows-latest runner.
"""
import os
import shutil
import subprocess
import sys
import tempfile

FORBIDDEN_PARTITIONS = [
    'preloader', 'nvram', 'nvdata', 'nvcfg', 'proinfo',
    'protect1', 'protect2', 'persist', 'seccfg', 'frp',
    'metadata', 'expdb', 'para', 'misc'
]

def run_cmd(cmd, cwd, input_str=None, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    p = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_str,
        text=True,
        capture_output=True,
        env=full_env,
        shell=True
    )
    return p

def test_corruption_detection(work_dir):
    print("\n[TEST] Corruption Detection on 1_reassemble.bat...")
    temp_dir = tempfile.mkdtemp(prefix="corrupt_test_")
    try:
        # Copy package files to temp directory
        for item in os.listdir(work_dir):
            s = os.path.join(work_dir, item)
            d = os.path.join(temp_dir, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
        
        # Find a part file or small image file to corrupt
        part_files = [f for f in os.listdir(temp_dir) if '.part' in f or f.endswith('.img')]
        if not part_files:
            raise RuntimeError("No image or part file found to test corruption.")
        
        target_corrupt = os.path.join(temp_dir, part_files[0])
        print(f"  Deliberately corrupting 1 byte in {part_files[0]}...")
        with open(target_corrupt, 'r+b') as f:
            b = f.read(1)
            f.seek(0)
            f.write(bytes([(b[0] ^ 0xFF) if b else 0xAA]))
        
        # Remove joined file if already present to force reassembly check
        joined_base = part_files[0].split('.part')[0]
        if os.path.exists(os.path.join(temp_dir, joined_base)):
            os.remove(os.path.join(temp_dir, joined_base))
        
        res = run_cmd("1_reassemble.bat", cwd=temp_dir, input_str="N\n")
        print(f"  Return code: {res.returncode}")
        if res.returncode == 0:
            print("STDERR:\n", res.stderr)
            print("STDOUT:\n", res.stdout)
            raise AssertionError("1_reassemble.bat succeeded on corrupted file! Expected failure.")
        
        assert "mismatch" in res.stdout.lower() or "error" in res.stdout.lower() or res.returncode != 0
        print("  [PASS] 1_reassemble.bat correctly rejected corrupted part and aborted.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_flash_stock_b(work_dir, stub_bin_dir):
    print("\n[TEST] 2_flash_stock_b.bat Flashing Execution against Stub Fastboot...")
    log_file = os.path.join(tempfile.gettempdir(), "fastboot_test_stock.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    flag_file = os.path.join(tempfile.gettempdir(), "fastboot_is_userspace.flag")
    if os.path.exists(flag_file):
        os.remove(flag_file)
    
    env = {
        'PATH': f"{stub_bin_dir};{os.environ['PATH']}",
        'FASTBOOT_LOG': log_file
    }
    
    # Run happy path with wipe=N
    print("  Running 2_flash_stock_b.bat (Input: YES, Wipe: N, Reboot: Y)...")
    res = run_cmd("2_flash_stock_b.bat", cwd=work_dir, input_str="YES\nN\nY\n", env=env)
    print(f"  Return code: {res.returncode}")
    if res.returncode != 0:
        print("STDOUT:\n", res.stdout)
        print("STDERR:\n", res.stderr)
        raise AssertionError("2_flash_stock_b.bat failed on happy path test.")
    
    with open(log_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
    
    print(f"  Captured {len(commands)} fastboot commands.")
    
    # 1. Assert forbidden partitions never appear in any command
    for cmd in commands:
        for forbidden in FORBIDDEN_PARTITIONS:
            assert forbidden not in cmd.lower(), f"CRITICAL SAFETY VIOLATION: Forbidden partition '{forbidden}' in command: {cmd}"
    print("  [PASS] Forbidden partitions guard: No sensitive/IMEI partitions touched.")
    
    # 2. Assert all flash targets end with _b (never _a)
    for cmd in commands:
        if cmd.startswith("flash"):
            parts = cmd.split()
            # flash [--flags] target image
            target = parts[1]
            if target.startswith("--"):
                target = parts[3]
            assert target.endswith("_b"), f"SLOT VIOLATION: Flash target '{target}' does not end in _b: {cmd}"
            assert not target.endswith("_a"), f"SLOT VIOLATION: Flash target '{target}' targets slot A: {cmd}"
    print("  [PASS] Slot guard: All flash targets strictly point to slot B (_b).")
    
    # 3. Assert vbmeta has both disable flags
    vbmeta_cmd = next((c for c in commands if "flash" in c and "vbmeta_b" in c), None)
    assert vbmeta_cmd is not None, "vbmeta_b was not flashed!"
    assert "--disable-verity" in vbmeta_cmd, "vbmeta_b missing --disable-verity"
    assert "--disable-verification" in vbmeta_cmd, "vbmeta_b missing --disable-verification"
    print("  [PASS] AVB guard: vbmeta_b flashed with --disable-verity --disable-verification.")
    
    # 4. Assert stage transition order: physical before reboot fastboot, logical after
    idx_reboot_fastboot = next(i for i, c in enumerate(commands) if "reboot fastboot" in c)
    idx_boot = next(i for i, c in enumerate(commands) if "flash" in c and "boot_b" in c)
    idx_system = next(i for i, c in enumerate(commands) if "flash" in c and "system_b" in c)
    
    assert idx_boot < idx_reboot_fastboot, "boot_b was not flashed before reboot fastboot!"
    assert idx_system > idx_reboot_fastboot, "system_b was not flashed after reboot fastboot!"
    print("  [PASS] Stage order: Physical partitions in bootloader -> reboot fastboot -> logical partitions in fastbootd.")
    
    # 5. Assert slot B activation and reboot
    assert any("--set-active=b" in c for c in commands), "fastboot --set-active=b was not called!"
    assert any(c == "reboot" for c in commands), "fastboot reboot was not called!"
    assert not any("-w" in c for c in commands), "Wipe (-w) was called despite answering N!"
    print("  [PASS] Finalization: --set-active=b set, reboot executed, wipe omitted.")

def test_wipe_confirmation(work_dir, stub_bin_dir):
    print("\n[TEST] 2_flash_stock_b.bat Wipe Confirmation (Wipe: Y)...")
    log_file = os.path.join(tempfile.gettempdir(), "fastboot_test_wipe.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    flag_file = os.path.join(tempfile.gettempdir(), "fastboot_is_userspace.flag")
    if os.path.exists(flag_file):
        os.remove(flag_file)
    
    env = {
        'PATH': f"{stub_bin_dir};{os.environ['PATH']}",
        'FASTBOOT_LOG': log_file
    }
    
    res = run_cmd("2_flash_stock_b.bat", cwd=work_dir, input_str="YES\nY\nY\n", env=env)
    assert res.returncode == 0, "Script failed on wipe=Y run"
    
    with open(log_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
    
    assert any("-w" in c for c in commands), "fastboot -w was not executed when user typed Y!"
    print("  [PASS] Wipe confirmation: fastboot -w executed when confirmed with Y.")

def test_failure_stop(work_dir, stub_bin_dir):
    print("\n[TEST] 2_flash_stock_b.bat Failure Injection (Simulated failure on vendor_boot_b)...")
    log_file = os.path.join(tempfile.gettempdir(), "fastboot_test_fail.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    flag_file = os.path.join(tempfile.gettempdir(), "fastboot_is_userspace.flag")
    if os.path.exists(flag_file):
        os.remove(flag_file)
    
    env = {
        'PATH': f"{stub_bin_dir};{os.environ['PATH']}",
        'FASTBOOT_LOG': log_file,
        'FASTBOOT_FAIL_ON': 'vendor_boot_b'
    }
    
    res = run_cmd("2_flash_stock_b.bat", cwd=work_dir, input_str="YES\nN\nY\n", env=env)
    assert res.returncode != 0, f"Script returned {res.returncode}; expected non-zero failure code!"
    
    with open(log_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
    
    # Assert execution stopped at vendor_boot_b and never reached reboot fastboot or system_b
    assert not any("reboot fastboot" in c for c in commands), "reboot fastboot was executed after failure!"
    assert not any("system_b" in c for c in commands), "system_b was executed after failure!"
    assert not any("reboot" == c for c in commands), "reboot was executed after failure!"
    print("  [PASS] Failure stop guard: Execution immediately halted upon failure with no further commands.")

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <work_dir> <stub_bin_dir>")
        sys.exit(1)
    
    work_dir = os.path.abspath(sys.argv[1])
    stub_bin_dir = os.path.abspath(sys.argv[2])
    
    print("================================================================")
    print(" RUNNING ACCEPTANCE TESTS FOR STOCK PACKAGE (SLOT B)")
    print("================================================================")
    
    test_corruption_detection(work_dir)
    test_flash_stock_b(work_dir, stub_bin_dir)
    test_wipe_confirmation(work_dir, stub_bin_dir)
    test_failure_stop(work_dir, stub_bin_dir)
    
    print("\n================================================================")
    print(" ALL STOCK PACKAGE ACCEPTANCE TESTS PASSED!")
    print("================================================================")

if __name__ == '__main__':
    main()
