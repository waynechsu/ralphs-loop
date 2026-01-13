# 🍩 Ralph Wiggum Loop for Antigravity IDE

> *"I'm a unitard!"* — Ralph Wiggum

**An experimental implementation of the "Ralph Wiggum Loop" pattern for the Antigravity IDE.**

This project demonstrates how to achieve **autonomous, stateless agent execution** by driving the IDE via the Chrome DevTools Protocol (CDP).

## 🧠 The Concept

The "Ralph Wiggum Loop" is a design pattern for autonomous agents:
1.  **Fresh Context**: Examples, history, and "learnings" are cleared after *every* single task.
2.  **External Memory**: State is persisted only in file artifacts (like `task.md`), not in the LLM's context window.
3.  **"The Gutter" Avoidance**: By resetting the environment consistently, we prevent the degradation of reasoning that happens in long-running chat sessions.

## 🏗️ Architecture

- **`wiggum_driver.py`**: A Python script that acts as the "Manager". It connects to Antigravity via CDP (Port 9000).
- **`.agent/task.md`**: The external memory. A persistent checklist of tasks.
- **`.agent/workflows/ralph_mode.md`**: The strict behavioral instructions for the agent.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- [Antigravity IDE](https://antigravity.dev) (or compatible fork)
- `pip install -r requirements.txt`

### Usage

1.  **Launch Antigravity with Remote Debugging**
    ```bash
    ./launch_ide.sh
    ```
    *(This ensures the IDE listens on port 9000)*

2.  **Define your Tasks**
    Edit `.agent/task.md` with your objectives:
    ```markdown
    - [ ] **Action**: Refactor login page → **Outcome**: Run tests
    ```

3.  **Run the Driver**
    ```bash
    python3 wiggum_driver.py
    ```

The driver will now autonomously:
1.  Read the next task.
2.  Inject it into the IDE.
3.  Wait for completion (detected via file update).
4.  **Rotate Context** (reload the page/clear session).
5.  Repeat!

## ⚠️ Safety Notes

- **Turbo Mode**: For full autonomy, set your IDE Review Policy to "Always Proceed".
- **Sandboxing**: Ensure your IDE has a "Terminal Command Deny List" enabled (e.g., blocking `rm -rf`) since the agent runs autonomously.

## 🛠️ Applying to Other Projects

To use this on a real project (e.g., your web app):

1.  **Copy Files**: Copy `wiggum_driver.py`, `launch_ide.sh`, and `requirements.txt` to your project root.
2.  **Create Folders**: Make sure `.agent/` and `.agent/workflows/` exist.
3.  **Copy Workflow**: Copy `ralph_mode.md` into `.agent/workflows/`.
4.  **Define Tasks**: Create `.agent/task.md`.
5.  **Launch**: Run `./launch_ide.sh` and then `python3 wiggum_driver.py`.

## License

MIT
