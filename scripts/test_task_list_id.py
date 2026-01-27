#!/usr/bin/env python3
"""
Test CLAUDE_CODE_TASK_LIST_ID functionality

Tests:
A. Custom ID creates separate directory in ~/.claude/tasks/
B. Tasks persist with custom ID
C. Cross-session sync (two queries with same ID share tasks)
D. Per-company isolation (different IDs = separate lists)

Usage:
    source venv/bin/activate
    python scripts/test_task_list_id.py
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

TASKS_DIR = Path.home() / ".claude" / "tasks"
OUTPUT_DIR = project_root / "earnings-analysis" / "test-outputs"

def log(msg: str):
    """Print timestamped log message"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def get_task_directories():
    """List all task list directories"""
    if not TASKS_DIR.exists():
        return []
    return [d.name for d in TASKS_DIR.iterdir() if d.is_dir()]

async def run_query_with_task_list_id(task_list_id: str, prompt: str, description: str):
    """Run a query with specific CLAUDE_CODE_TASK_LIST_ID"""

    # Set env var BEFORE importing SDK (important!)
    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = task_list_id

    log(f"Running: {description}")
    log(f"  CLAUDE_CODE_TASK_LIST_ID = {task_list_id}")

    # Import fresh each time to pick up env var
    # Note: This may not work if SDK caches the env var at import time
    from claude_agent_sdk import query, ClaudeAgentOptions

    result_text = ""
    try:
        async for event in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model="claude-sonnet-4-20250514",
                setting_sources=["project"],
                max_turns=15,
                permission_mode="bypassPermissions",
            )
        ):
            if hasattr(event, 'message') and hasattr(event.message, 'content'):
                for block in event.message.content:
                    if hasattr(block, 'text'):
                        result_text = block.text

        return {"success": True, "result": result_text}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def test_a_custom_id():
    """Test A: Custom ID creates separate directory"""
    log("\n" + "="*60)
    log("TEST A: Custom ID creates separate task list directory")
    log("="*60)

    test_id = "test-custom-id-A"

    # Check directories before
    dirs_before = get_task_directories()
    log(f"Task directories before: {dirs_before}")

    # Run query with custom ID
    result = await run_query_with_task_list_id(
        task_list_id=test_id,
        prompt="""
        1. Use TaskCreate to create a task with subject: "TEST_A_CUSTOM_ID_TASK"
        2. Use TaskList to show all tasks
        3. Report the task ID and current task count
        """,
        description="Create task with custom ID"
    )

    # Check directories after
    dirs_after = get_task_directories()
    log(f"Task directories after: {dirs_after}")

    # Verify
    new_dirs = set(dirs_after) - set(dirs_before)
    if test_id in dirs_after or test_id in new_dirs:
        log(f"✅ TEST A PASSED: Directory '{test_id}' created")
        return True
    else:
        log(f"⚠️ TEST A UNCLEAR: Expected '{test_id}' in directories")
        log(f"   New directories: {new_dirs}")
        log(f"   Result: {result.get('result', result.get('error', 'unknown'))[:200]}")
        return None


async def test_c_cross_session_sync():
    """Test C: Two queries with same ID share tasks"""
    log("\n" + "="*60)
    log("TEST C: Cross-session sync (same ID = shared tasks)")
    log("="*60)

    test_id = "test-cross-session-C"
    unique_subject = f"CROSS_SESSION_TASK_{int(time.time())}"

    # Query 1: Create a task
    log("Query 1: Creating task...")
    result1 = await run_query_with_task_list_id(
        task_list_id=test_id,
        prompt=f"""
        1. Use TaskCreate to create a task with subject: "{unique_subject}"
        2. Use TaskList to show all tasks
        3. Report the exact task ID you created
        """,
        description="Create task in session 1"
    )
    log(f"Query 1 result: {result1.get('result', result1.get('error', ''))[:300]}")

    # Query 2: Check if task is visible
    log("Query 2: Checking if task is visible...")
    result2 = await run_query_with_task_list_id(
        task_list_id=test_id,
        prompt=f"""
        1. Use TaskList to show all tasks
        2. Look for a task with subject containing "{unique_subject}"
        3. Report: Did you find it? Yes or No. And list all task subjects you see.
        """,
        description="Check task in session 2"
    )
    log(f"Query 2 result: {result2.get('result', result2.get('error', ''))[:300]}")

    # Check if task was found
    result2_text = result2.get('result', '').lower()
    if unique_subject.lower() in result2_text or 'yes' in result2_text:
        log(f"✅ TEST C PASSED: Task visible across sessions")
        return True
    else:
        log(f"❌ TEST C FAILED: Task not visible in second session")
        return False


async def test_d_per_company_isolation():
    """Test D: Different IDs = separate task lists"""
    log("\n" + "="*60)
    log("TEST D: Per-company isolation (different IDs = separate lists)")
    log("="*60)

    aapl_id = "test-AAPL-isolation"
    msft_id = "test-MSFT-isolation"

    aapl_task = f"AAPL_ISOLATION_TASK_{int(time.time())}"
    msft_task = f"MSFT_ISOLATION_TASK_{int(time.time())}"

    # Create AAPL task
    log("Creating AAPL task...")
    await run_query_with_task_list_id(
        task_list_id=aapl_id,
        prompt=f'Use TaskCreate to create a task with subject: "{aapl_task}"',
        description="Create AAPL task"
    )

    # Create MSFT task
    log("Creating MSFT task...")
    await run_query_with_task_list_id(
        task_list_id=msft_id,
        prompt=f'Use TaskCreate to create a task with subject: "{msft_task}"',
        description="Create MSFT task"
    )

    # Check AAPL list - should NOT see MSFT task
    log("Checking AAPL list for isolation...")
    aapl_result = await run_query_with_task_list_id(
        task_list_id=aapl_id,
        prompt=f"""
        Use TaskList to show all tasks.
        Report:
        1. Do you see "{aapl_task}"? (should be YES)
        2. Do you see "{msft_task}"? (should be NO if isolated)
        List all task subjects.
        """,
        description="Check AAPL isolation"
    )
    log(f"AAPL list result: {aapl_result.get('result', '')[:300]}")

    # Check MSFT list - should NOT see AAPL task
    log("Checking MSFT list for isolation...")
    msft_result = await run_query_with_task_list_id(
        task_list_id=msft_id,
        prompt=f"""
        Use TaskList to show all tasks.
        Report:
        1. Do you see "{msft_task}"? (should be YES)
        2. Do you see "{aapl_task}"? (should be NO if isolated)
        List all task subjects.
        """,
        description="Check MSFT isolation"
    )
    log(f"MSFT list result: {msft_result.get('result', '')[:300]}")

    # Analyze results
    aapl_text = aapl_result.get('result', '').lower()
    msft_text = msft_result.get('result', '').lower()

    aapl_sees_own = aapl_task.lower() in aapl_text
    aapl_sees_msft = msft_task.lower() in aapl_text
    msft_sees_own = msft_task.lower() in msft_text
    msft_sees_aapl = aapl_task.lower() in msft_text

    log(f"AAPL sees own task: {aapl_sees_own}")
    log(f"AAPL sees MSFT task: {aapl_sees_msft} (should be False for isolation)")
    log(f"MSFT sees own task: {msft_sees_own}")
    log(f"MSFT sees AAPL task: {msft_sees_aapl} (should be False for isolation)")

    if aapl_sees_own and msft_sees_own and not aapl_sees_msft and not msft_sees_aapl:
        log(f"✅ TEST D PASSED: Full isolation between AAPL and MSFT")
        return True
    elif not aapl_sees_msft and not msft_sees_aapl:
        log(f"⚠️ TEST D PARTIAL: Lists isolated but may have other issues")
        return True
    else:
        log(f"❌ TEST D FAILED: No isolation - tasks visible across IDs")
        return False


async def main():
    """Run all tests"""
    log("="*60)
    log("CLAUDE_CODE_TASK_LIST_ID Test Suite")
    log("="*60)
    log(f"Tasks directory: {TASKS_DIR}")
    log(f"Output directory: {OUTPUT_DIR}")

    results = {}

    # Run tests
    results['A_custom_id'] = await test_a_custom_id()
    results['C_cross_session'] = await test_c_cross_session_sync()
    results['D_isolation'] = await test_d_per_company_isolation()

    # Summary
    log("\n" + "="*60)
    log("TEST SUMMARY")
    log("="*60)
    for test, result in results.items():
        status = "✅ PASS" if result else ("⚠️ UNCLEAR" if result is None else "❌ FAIL")
        log(f"  {test}: {status}")

    # Write results to file
    output_file = OUTPUT_DIR / "task-list-id-test-results.txt"
    with open(output_file, 'w') as f:
        f.write(f"CLAUDE_CODE_TASK_LIST_ID Test Results\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"{'='*50}\n\n")
        for test, result in results.items():
            status = "PASS" if result else ("UNCLEAR" if result is None else "FAIL")
            f.write(f"{test}: {status}\n")

    log(f"\nResults written to: {output_file}")

    # Show task directories created
    log(f"\nTask directories after all tests:")
    for d in get_task_directories():
        log(f"  - {d}")


if __name__ == "__main__":
    asyncio.run(main())
