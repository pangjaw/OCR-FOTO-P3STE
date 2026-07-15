# Project Rules & Agent Instructions

If you are an AI assistant working on this repository, please follow these guidelines to keep the project context organized.

## 🗂️ Knowledge Vault (Obsidian)
This repository is configured as an **Obsidian Vault**. The workspace metadata and notes are stored at the root and in the `Notes/` directory:
- [[Dashboard.md]] - Main entry point linking to all logs, code files, and decisions (patokan utama).
- [[README.md]] - Contains the project goals and constraints.
- [[setup.md]] - Contains environment setup and usage commands.
- [[Notes/Daily/|Notes/Daily/]] - Holds daily update logs.
- [[Notes/Decisions/|Notes/Decisions/]] - Architectural Decision Records (ADRs).
- [[Notes/Templates/|Notes/Templates/]] - Reusable note templates.

## 🤖 Instructions for AI Assistants
1. **Read AGENTS.md First:** Always read the root [[AGENTS.md]] **before making ANY edits or proposing plans.** It contains the complete code map, function reference, data flow pipeline, and domain glossary.
2. **Read Dashboard.md Second:** After AGENTS.md, read [[Dashboard.md]] for current task statuses.
3. **Update After Working:** When you finish a task, update [[Dashboard.md]] if task statuses change.
4. **Daily Logs:** If a new day starts, feel free to create a new log in `Notes/Daily/YYYY-MM-DD.md` using the [[Notes/Templates/Template - Daily Note|Template - Daily Note.md]] format.
5. **Debug & Fix Rule (CRITICAL):** Jika user meminta "debug ocr dan stage nya" (atau perintah investigasi serupa), AI assistant **CUKUP** menampilkan hasil pembacaan OCR / data deteksi internal serta menjelaskan mengapa stage tersebut terpilih. **JANGAN langsung melakukan perbaikan/modifikasi kode (fix/edit file program) sebelum ada perintah atau konfirmasi persetujuan tertulis dari user!**
