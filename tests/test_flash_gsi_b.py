#!/usr/bin/env python3
"""
Acceptance test suite for TECNO KL5 Slot B Axion GSI Package on Windows.
Runs under windows-latest runner.
"""
import os
import shutil
import subprocess
import sys
import tempfile

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

def test_flash_gsi_b(work_dir, stub_bin_dir):
    print("\n[TEST] 3_flash_gsi_b.bat Flashing Execution against Stub Fastboot...")
    log_file = os.path.join(tempfile.gettempdir(), "fastboot_test_gsi.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    flag_file = os.path.join(tempfile.gettempdir(), "fastboot_is_userspace.flag")
    if os.path.exists(flag_file):
        os.remove(flag_file)
    
    env = {
        'PATH': f"{stub_bin_dir};{os.environ['PATH']}",
        'FASTBOOT_LOG': log_file
    }
    
    print("  Running 3_flash_gsi_b.bat (Input: YES, Wipe: Y, Reboot: Y)...")
    res = run_cmd("3_flash_gsi_b.bat", cwd=work_dir, input_str="YES\nY\nY\n", env=env)
    print(f"  Return code: {res.returncode}")
    if res.returncode != 0:
        print("STDOUT:\n", res.stdout)
        print("STDERR:\n", res.stderr)
        raise AssertionError("3_flash_gsi_b.bat failed on happy path.")
    
    with open(log_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
    
    # 1. vbmeta flashed with disable flags
    vbmeta_cmd = next((c for c in commands if "flash" in c and "vbmeta_b" in c), None)
    assert vbmeta_cmd is not None, "vbmeta_b was not flashed!"
    assert "--disable-verity" in vbmeta_cmd and "--disable-verification" in vbmeta_cmd, "vbmeta_b missing disable flags"
    print("  [PASS] AVB guard: vbmeta_b flashed with --disable-verity --disable-verification.")
    
    # 2. Reboot fastboot called
    assert any("reboot fastboot" in c for c in commands), "reboot fastboot was not called!"
    
    # 3. product_b and system_ext_b deleted to avoid conflicts
    assert any("delete-logical-partition product_b" in c for c in commands), "product_b was not deleted!"
    assert any("delete-logical-partition system_ext_b" in c for c in commands), "system_ext_b was not deleted!"
    print("  [PASS] Partition cleanup: product_b and system_ext_b cleared for clean Treble GSI environment.")
    
    # 4. GSI flashed to system_b
    assert any("flash system_b system.img" in c for c in commands), "system_b was not flashed with system.img!"
    print("  [PASS] GSI target: Axion 2.9 GSI flashed to system_b.")
    
    # 5. Userdata wipe
    assert any("-w" in c for c in commands), "Wipe (-w) was not executed!"
    
    # 6. Slot activation & reboot
    assert any("--set-active=b" in c for c in commands), "--set-active=b was not called!"
    assert any(c == "reboot" for c in commands), "reboot was not called!"
    print("  [PASS] Slot B activation & reboot executed.")

def test_gsi_failure_stop(work_dir, stub_bin_dir):
    print("\n[TEST] 3_flash_gsi_b.bat Failure Injection (Simulated failure on system_b)...")
    log_file = os.path.join(tempfile.gettempdir(), "fastboot_test_gsi_fail.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    flag_file = os.path.join(tempfile.gettempdir(), "fastboot_is_userspace.flag")
    if os.path.exists(flag_file):
        os.remove(flag_file)
    
    env = {
        'PATH': f"{stub_bin_dir};{os.environ['PATH']}",
        'FASTBOOT_LOG': log_file,
        'FASTBOOT_FAIL_ON': 'system_b'
    }
    
    res = run_cmd("3_flash_gsi_b.bat", cwd=work_dir, input_str="YES\nY\nY\n", env=env)
    assert res.returncode != 0, f"Expected non-zero return code, got {res.returncode}"
    
    with open(log_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
    
    # Assert execution stopped and never called --set-active=b or reboot
    assert not any("--set-active=b" in c for c in commands), "--set-active=b executed after failure!"
    assert not any(c == "reboot" for c in commands), "reboot executed after failure!"
    print("  [PASS] Failure stop guard: Execution stopped at failure with no slot switch or reboot.")

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <work_dir> <stub_bin_dir>")
        sys.exit(1)
    
    work_dir = os.path.abspath(sys.argv[1])
    stub_bin_dir = os.path.abspath(sys.argv[2])
    
    print("================================================================")
    print(" RUNNING ACCEPTANCE TESTS FOR AXION GSI PACKAGE (SLOT B)")
    print("================================================================")
    
    test_flash_gsi_b(work_dir, stub_bin_dir)
    test_gsi_failure_stop(work_dir, stub_bin_dir)
    
    print("\n================================================================")
    print(" ALL AXION GSI ACCEPTANCE TESTS PASSED!")
    print("================================================================")

if __name__ == '__main__':
    main()
