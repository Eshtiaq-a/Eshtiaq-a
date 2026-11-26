# PROJECT PLAN & ARCHITECTURE SPECIFICATION — ESHTIAQ DEVELOPER UNIVERSE

**GitHub Profile:** `Eshtiaq-a` (Eshtiaq Ahmad)  
**Target Repository:** `https://github.com/Eshtiaq-a/Eshtiaq-a.git`  
**Document Status:** Accepted Architectural Baseline — Awaiting Phase 0 & Phase 1 Authorization  
**Revision Date:** 2026-11-26  

---

## 1. Executive Summary

**Eshtiaq Developer Universe** is a fully automated, data-driven GitHub profile experience for `Eshtiaq-a` built using Python 3, SVG/GIF graphics, GitHub Flavored Markdown, and GitHub Actions. Every statistic, commit credit, language distribution, and repository card is generated reproducibly from official public APIs with zero paid services and zero hardcoded project data.

The profile preserves **exactly three primary visual sections**, anchored to the supplied visual references:
1. **Section 01 — Pixel-Art Developer Workspace & GitHub Movie End Credits:** A faithful dark pixel-art personal bedroom/workspace centered on a dual-device Apple Mac setup — one **MacBook** (displaying a subtle desktop/terminal interface) visibly connected to a **separate, larger external monitor** acting as the primary focal point. The external monitor continuously scrolls `Eshtiaq-a`'s public commit history across **all accessible public branches** as cinematic movie end credits (`SVG-first` experimental choice, with an `animated GIF fallback` gated by live GitHub testing). The room includes 1–2 subtle indoor plants, warm desk lighting, zero female characters (character optional; male developer only if ever included), and decoupled optional decorative modules (Dhaka weather, live clock, language bookshelf).
2. **Section 02 — Authentic Neofetch Developer Terminal:** A dark terminal SVG faithfully replicating the supplied Neofetch reference (`#0d0f14` canvas, blue border, green ASCII portrait, aligned dot-leaders, bio, contact links, and live GitHub statistics).
3. **Section 03 — Automatic Repository Explorer (Approved Option A):** A `#080c18` dark showcase aligned with the third reference image (`Built, shipped, shared` overview header/constellation/timeline + auto-generated **clickable individual project cards** for **all** public repositories owned by `Eshtiaq-a`).

---

## 2. Project Objectives

1. **Preserve Visual Identity:** Match the color palettes, proportions, spacing, typography, and dark-mode composition of all three supplied reference screenshots without falling back to generic templates.
2. **Comprehensive Multi-Branch Movie End Credits:** Collect commits across **all accessible public branches** of every public repository owned by `Eshtiaq-a`, deduplicate by `(repository_id, commit_sha)`, sort chronologically oldest-to-newest, and render a seamless looping film-credit roll ending with `"THE END? — THE JOURNEY CONTINUES."`.
3. **Zero-Maintenance Repository Discovery:** Automatically discover, sort, and render clickable project cards for all public repositories (including newly created repos, empty repos, archived repos, and repos missing descriptions or languages).
4. **Verified GitHub Rendering Reliability:** Validate animated SVG rendering directly inside GitHub's Camo `<img>` proxy first, retaining an optimized animated GIF fallback path if any browser/proxy limitation degrades scrolling or looping.
5. **Clean Engineering & Security Hygiene:** Enforce PEP 8, Python type hints, modular architecture, strict SVG/Markdown escaping, JSON/XML validation gates, least-privilege GitHub Actions permissions, and automated tests.

---

## 3. Approved Architecture Decisions

| Decision Area | Approved Strategy | Architectural Consequence |
|---|---|---|
| **Decision 01: Commit History** | **All accessible public branches** | Traverse `GET /users/{user}/repos` → `GET /repos/{owner}/{repo}/branches` → paginated `GET /repos/{owner}/{repo}/commits?sha={branch}`, deduplicating via `(repo_id, sha)` and ordering oldest-to-newest. |
| **Decision 02: Repository Explorer** | **Option A (Overview + Clickable Cards)** | Render a `Built, shipped, shared` overview visual (`#080c18` style) followed by individual clickable `<a href="..."><img src="..."></a>` SVG cards for every public repository owned by `Eshtiaq-a`. |
| **Decision 03: Decorative Features** | **Optional enhancements** | Dynamic Dhaka weather, live Dhaka clock, and language bookshelves are toggleable plugins in `config/profile.json` that degrade safely to reference defaults without external dependencies. |
| **Decision 04: Movie Credit Animation** | **SVG experimental first choice, GIF fallback** | Build & test an experimental animated SVG (`@keyframes` + `<clipPath>`) inside live GitHub `README.md` via Camo first; do not rely on SVG animation until verified, and switch to optimized animated GIF (`< 5 MB`) if proxy/rendering verification fails. |

---

## 4. Critical Git Repository Issue & Resolution Plan

### 4.1 Read-Only Inspection Findings

Both local Git directories were inspected without modifying, deleting, moving, or initializing anything:

| Path | Created Timestamp | `HEAD` & Branch | Remote `origin` | Objects / Refs / Logs | Contents |
|---|---|---|---|---|---|
| **Outer:** `/Users/eshtiaqahmad/git profile/Eshtiaq-a/.git` | `2026-11-26 22:04:01–02` | `ref: refs/heads/main` (`No commits yet`) | `https://github.com/Eshtiaq-a/Eshtiaq-a.git` | Empty (`0` objects, `0` refs, no `.git/logs`) | Workspace root holds `PROJECT_PLAN.md` and untracked `Eshtiaq-a/` |
| **Inner:** `/Users/eshtiaqahmad/git profile/Eshtiaq-a/Eshtiaq-a/.git` | `2026-11-26 22:04:22–23` | `ref: refs/heads/main` (`No commits yet`) | `https://github.com/Eshtiaq-a/Eshtiaq-a.git` | Empty (`0` objects, `0` refs, no `.git/logs`) | Completely empty folder (`total 0`) aside from `.git/` |

- **Actual Antigravity Workspace:** `/Users/eshtiaqahmad/git profile/Eshtiaq-a` (both Active Workspace and Command Working Directory).
- **Remote State:** `git ls-remote origin` returned empty; GitHub REST API confirms `Eshtiaq-a/Eshtiaq-a` is public (`created_at: 2026-11-26T15:45:28Z`) and currently empty (`HTTP 409 Conflict` on `/commits`, `0` branches).

### 4.2 Risks of Retaining Nested Git Repositories

1. **Broken Gitlink (`160000` Mode):** Running `git add .` in the outer repository while an inner `.git/` exists registers `Eshtiaq-a` as an embedded submodule/gitlink without a `.gitmodules` file, causing `actions/checkout` and `git clone --recursive` failures.
2. **Split Commits & Lost History:** Commits run inside the inner folder will never appear in the outer workspace root (and vice versa), creating divergent empty histories against the same remote.
3. **Path Confusion:** Profile `README.md` must live at the repository root (`README.md`) to render on `github.com/Eshtiaq-a`; placing code in an inner nested repository creates a redundant `Eshtiaq-a/Eshtiaq-a/` hierarchy locally.

### 4.3 Recommended Root & Approval-Gated Cleanup Commands

- **Recommendation:** Retain the **outer repository** (`/Users/eshtiaqahmad/git profile/Eshtiaq-a`) as the single canonical project root and remove the empty nested inner directory `/Users/eshtiaqahmad/git profile/Eshtiaq-a/Eshtiaq-a`.
- **DO NOT EXECUTE YET — Requires explicit human approval prior to Phase 1:**

```bash
# 1. Re-verify working directory and confirm inner folder holds nothing besides .git/
pwd
ls -la "/Users/eshtiaqahmad/git profile/Eshtiaq-a/Eshtiaq-a"
find "/Users/eshtiaqahmad/git profile/Eshtiaq-a/Eshtiaq-a/.git/objects" -type f

# 2. Only after confirming zero files/objects above, remove the empty nested directory:
rm -rf "/Users/eshtiaqahmad/git profile/Eshtiaq-a/Eshtiaq-a"

# 3. Verify single clean repository root linked to origin:
git -C "/Users/eshtiaqahmad/git profile/Eshtiaq-a" status
git -C "/Users/eshtiaqahmad/git profile/Eshtiaq-a" remote -v
```

### 4.4 Live Public GitHub Baseline Snapshot (Read-Only, 2026-11-26)

- **Profile:** `login="Eshtiaq-a"`, `name="Eshtiaq Ahmad"`, `location="dhaka , bangladesh "`, `created_at="2025-12-29T09:03:03Z"`, `public_repos=8`, `followers=2`, `following=4`.
- **Public Repositories & Branch Discovery:**
  - `assignment_1` (`HTML`, 1 branch `main`, 2 commits, `description: null`)
  - `C-code-Practices-` (`C`, 1 branch `main`, 3 commits)
  - `Clear-Cut-` (`TypeScript`, 2 branches `main` [13] + `sub/test-branch` [1], `homepage: https://clear-cut-seven.vercel.app`)
  - `Eshtiaq-a` (`language: null`, 0 branches, empty repo `HTTP 409`, `description: null`)
  - `Portfolio-main` (`TypeScript`, 1 branch `main`, 1 commit, `homepage: https://portfolio-main-gilt-nu.vercel.app`)
  - `stash-money-manager` (`TypeScript`, 3 branches `main` [14] + `vercel/install-vercel-web-analytics-def6k2` [13] + `vercel/install-vercel-web-analytics-yhmtcy` [14], `homepage: https://stash-saver.vercel.app/`)
  - `test` (`HTML`, 1 branch `main`, 1 commit, `description: null`)
  - `Wrechship` (`Python`, 1 branch `main`, 31 commits, `homepage: https://www.wreckship.me/`)
- **Multi-Branch Deduplication Evidence:** Across all 10 accessible branch heads, raw branch traversal yielded **93** commit entries that deduplicate via `(repo_id, sha)` to **68 unique commits** (`25` shared branch-ancestor commits eliminated, `0` merge commits currently).

---

## 5. Comprehensive Visual Design Specification & Acceptance Criteria

All palette colors and spatial ratios are measured directly from the three supplied reference screenshots (`ref1.jpg`: `1024x636`, `ref2.jpg`: `1024x622`, `ref3.jpg`: `453x1024`).

### 5.1 Global Profile Layout & Responsive Compatibility

- **Three-Section Structure in `README.md`:**
  1. Section 01: Pixel-Art Developer Workspace + Caption
  2. Diamond-tipped divider (`✦ ─── ✦` or styled `<picture>`/`<svg>` divider matching Image 3)
  3. Section 02: Neofetch Developer Terminal
  4. Diamond-tipped divider
  5. Section 03: `Built, shipped, shared` Overview Card + Clickable Per-Repo Card Grid
- **GitHub Compatibility & Responsiveness:**
  - All visual assets render inside standard `<img src="assets/...">` / `<a href="..."><img src="assets/..."></a>` tags with explicit `alt` text and `width="100%"` (or `width="48%"` in Option A 2-column grids).
  - SVG `viewBox` coordinates scale fluidly from GitHub desktop (`~890px–1012px` content column) down to mobile viewports (`~340px`) without horizontal overflow.
  - Self-contained dark backgrounds (`#1d2333`, `#0d0f14`, `#080c18`) guarantee identical legibility under both GitHub Dark and GitHub Light UI themes.

---

### 5.2 SECTION 01 — Pixel-Art Personal Workspace, MacBook + External Monitor & Movie Credits

- **Canvas & Dimensions:**
  - `viewBox="0 0 988 504"` (card aspect ratio `~1.96:1`, outer rounded corner `rx="14"`), matching the `987x503` card measured in `ref1.jpg`.
  - Virtual pixel grid locked to `2px` increments with `shape-rendering="crispEdges"` for razor-sharp pixel edges at every zoom level.
- **Redesigned Desk & Room Composition (`988x504` space, Zero Layout Collisions):**
  - **Wall Zone:** `x=0..988, y=0..395` (`78.4%` height) — vertical stripes alternating `#1d2333` and `#1b212f` (`18px` period).
  - **Floor Zone:** `x=0..988, y=395..504` (`21.6%` height) — horizontal wood planks `#3a2a23` with seam lines `#34251e` and staggered vertical joints.
  - **Window (Left Wall):** `x=36..244, y=55..257` (`208x202`, `2x2` frame `#0e1216`, wooden sill `#6a4a31`). Default state: deep night sky `#0a1a39`, stars `#4c5b7a`, L-shaped crescent moon `#f3e8d4` in upper-right pane (positioned cleanly left of the widened dual-device desk).
  - **Name Plaque (Centered Over External Monitor):** `x=366..738, y=50..98` (`372x48`), cream fill `#f3e9d5`, dark border `#14181e`, custom vector pixel-bitmap glyphs spelling **`ESHTIAQ AHMAD`** (`#14181e`, zero dependency on installed system fonts).
  - **Character & Avatar Rule (Mandatory):**
    - **Never** include a girl, female avatar, or female character anywhere in the workspace.
    - A human character is **optional** and omitted by default (matching `ref1.jpg`) so the MacBook and external monitor setup dominates the composition; if a human figure is ever included, it must represent a male developer.
  - **Redesigned Desk Surface (`x=256..732, y=298..322`, `476px` wide):**
    - Widened proportionally (`48.2%` of card width, `#6a4a31` tabletop, `#563926` apron `y=322..330`, legs `x=270..284` and `x=704..718` down to floor `y=395`) to seat the dual-device Mac setup naturally without crowding:
    - **Desk Lamp (`x=264..304`):** Warm gold shade (`#f2cb62`, `y=176..190`), slim stand (`x=282..286, y=190..298`), translucent warm light cone (`#f2cb62` at `7%` opacity) illuminating the MacBook and left desk edge.
    - **Apple MacBook Laptop (`x=310..404`, left-center on desk):**
      - Separate open laptop (`94px` wide): aluminum/space-gray unibody base (`x=310..404, y=288..298`, `#888b92` top / `#4c4d52` shadow) + angled display lid (`x=316..398, y=236..288`, `82x52` bezel `#4c4d52`, screen `#0c1a33` showing a **subtle miniature macOS desktop/terminal interface** — **never** the movie credits).
      - **Visible Display Connection:** Believable pixel USB-C / DisplayPort cable (`#1f212c` / `#4c4d52`) routing from the MacBook's right-side port (`x=402, y=292`) cleanly along the desk surface (`y=294..297`) into the back/stand of the external monitor (`x=536`).
    - **External Monitor — Primary Visual Focal Point (`x=418..686`, center-right on desk):**
      - Larger, visually prominent display (`268x164` outer bezel `x=418..686, y=122..286`, `#333338` bezel / `#1f212c` inner bevel, centered stand `x=538..566, y=286..294` + base `x=512..592, y=294..298`).
      - **Movie-Credit Screen Viewport (`246x142`):** `x=429..675, y=132..274`, deep navy-teal background `#0c1a33` / `#051b2b`. **Exclusively** hosts the cinematic vertical scrolling movie end credits with **100% unobstructed legibility**.
    - **Coffee Mug (`x=694..714, y=276..298`):** Cream pixel mug (`#ebe0cf`) with right handle and faint rising steam, cleanly right of the external monitor bezel (`x=686`).
  - **Foreground Chair (`x=520..592, y=306..395`):**
    - T-shaped dark slate-gray chair (`#3d4350` / `#4c4d52`) positioned cleanly below the monitor bezel line (`y >= 306`) so it reinforces the personal workspace silhouette without obstructing a single pixel of the external monitor's movie credits.
  - **Indoor Plants (1–2 Subtle Plants Only):**
    - **Plant 1 (Floor Left Beside Desk, `x=115..165, y=312..395`):** Terracotta pot (`#9a5a3a`/`#7a492c`) with pixel green leaves (`#2ca042`), resting naturally below the window left of the desk.
    - **Plant 2 (Optional Small Potted Plant, `x=780..812, y=252..294` on lower right shelf, OR far-right desk corner `x=716..730` if mug shifts left):** Subtle small potted pixel plant/succulent consistent with the room palette; **maximum 2 plants total**, no extra clutter.
  - **Right Wall & Floor Accents (Preserved from `ref1.jpg`):**
    - **Wall Clock:** (`cx=860, cy=73, r=27`, cream face `#f3e8d4`, dark ring `#12161a`).
    - **Two Bookshelves:** (`x=770..946`, `#6a4a31` / `#563926`, top shelf `y=198`, bottom shelf `y=294`, language book spines `#3472a5`, `#f4422e`, `#f8de55`, `#dad1c4`).
    - **Sleeping Orange Cat:** (floor right `x=776..876, y=366..395`, `#e8a55b` / `#c3803a`, subtle `z` sleep pixels).
- **Asset Requirements (Section 01):**
  - `assets/workspace.svg` (self-contained animated SVG, `< 450 KB`, zero external fonts, zero external raster images).
  - `data/sample_commits.json` (clearly labelled Phase 1 sample-data fixture) → replaced by `data/commits.json` in Phase 2.
  - `assets/workspace.gif` (generated by `src/gif_workspace.py` **only if** live GitHub SVG testing requires fallback, `< 1.5 MB` target).
- **Typography & Spacing (External Monitor Movie Credits):**
  - Monospace stack: `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`.
  - Credit block hierarchy (styled as cinematic film production credits, **not** a raw terminal log):
    - Opening card title: `10px–11px` uppercase gold/cream (`#f2cb62` / `#f3e8d4`), letter-spacing `1.2px`.
    - Repository header line: `9px` bold mint-cyan (`#93c8b2`), centered.
    - Commit message lines: `8.5px` off-white (`#e9ecf2`), max `36` chars/line, up to `2` wrapped lines.
    - Metadata line (`YYYY-MM-DD  •  Author`): `7.5px` muted slate-mint (`#7da79f` / `#a6b5cc`), `12px` gap before next credit entry.
    - Closing sequence: two-line finale **`"THE END?"`** / **`"THE JOURNEY CONTINUES."`**.
- **Optional Decorative Features (Decision 03):**
  - Controlled via `config/profile.json` booleans (`enable_weather`, `enable_live_clock`, `enable_language_bookshelf`).
  - Core MacBook + external monitor setup and cozy night room render deterministically even when all optional modules are disabled or offline.
- **Animation Behavior (Decision 04):**
  - Vertical continuous upward scroll inside `<clipPath id="monitor-screen-clip">` (`x=429, y=132, width=246, height=142`), seamless infinite loop via duplicated credit block (`0%` → `-100%` of single-sequence height), CSS `@keyframes` experimental first choice, GIF fallback ready if Camo testing reveals issues.
- **Visual Acceptance Criteria (Section 01):**
  - [ ] Room palette matches measured hexes within `±2` RGB units; crisp pixel edges (`crispEdges`) with zero anti-aliased blur.
  - [ ] Zero female character/avatar anywhere in the workspace (character omitted by default, or male developer only if ever included).
  - [ ] Desk visibly features a separate Apple MacBook (subtle desktop/terminal UI) connected by a believable display cable to a larger, visually prominent central external monitor.
  - [ ] Movie end-credit animation appears **exclusively** on the external monitor (never on the MacBook screen) and looks like cinematic production credits, not a plain terminal log.
  - [ ] `ESHTIAQ AHMAD` plaque is centered above the external monitor and crisp without external fonts.
  - [ ] One or two subtle indoor plants appear naturally (e.g., floor plant beside desk and/or small plant on shelf/desk) with no excessive decorative clutter.
  - [ ] Zero layout collisions: external monitor credit text never collides with chair, mug, MacBook, cable, or bezel edges.
  - [ ] Opening sequence, chronological commits (repo, message, date, author), and cinematic closing (`"THE END?"` / `"THE JOURNEY CONTINUES."`) scroll smoothly upward and loop naturally in live GitHub `README.md`.
  - [ ] Cozy personal bedroom/workspace atmosphere preserved from `ref1.jpg` with no `gitskins.com` third-party watermark.

---

### 5.3 SECTION 02 — Neofetch Developer Terminal

- **Canvas & Dimensions:**
  - `viewBox="0 0 1009 610"` (`~1.65:1` aspect ratio), rounded rectangle outer frame `rx="12"`, `1.5px` border `#7096c7`, background `#0d0f14`.
- **Exact Layout & Visual Hierarchy:**
  - **Top Command Prompt (`x=32, y=38`):** `eshtiaq-a@github` (`#64aee9`) + `:` + `~$` (`#a6b5cc`) + ` neofetch` (`#ebf0f4`).
  - **Left Column (`x=44..380`, ~35% width):** Green ASCII portrait silhouette (`#6b997c` / `#95c0a5`, `12px` monospace, `line-height: 14px`, ~28 rows × ~38 columns), stored deterministically in `assets/ascii_portrait.txt`.
  - **Right Column (`x=420..975`, ~55% width):** Fixed-column monospace grid (`13px` font, `line-height: 22px`):
    - Header `eshtiaq-a@github` (`#64aee9`) + rule (`#41444b`)
    - Primary rows (`Name`, `Role`, `Location`, `Uptime`, `Languages`): blue bullet `▪` (`#56a9ff`), blue label (`#64aee9`), calculated gray dot-leaders (`#888b92`), right-aligned off-white value (`#ebf0f4`).
    - `- About` section + rule: clean 2-line wrapped bio (`#ebf0f4`).
    - `- Contact` section + rule: `GitHub` (`github.com/eshtiaq-a`) plus configured public social/portfolio links.
    - `- GitHub Stats` section + rule: 2-column grid divided by `|` (`#51565d`):
      - `Repos` | `Stars`
      - `Followers` | `Following`
      - `Contributions` | `Active days`
      - `Streak` | `Best streak`
  - **Bottom Command Prompt (`x=32, y=576`):** `eshtiaq-a@github:~$ ` + solid blue cursor block (`#56a9ff`, `9x16`).
- **Animation & Compatibility:** Static crisp vector SVG (optional subtle cursor blink via CSS `@keyframes` only if verified harmless; static cursor matches Image 2 cleanly).
- **Visual Acceptance Criteria (Section 02):**
  - [ ] Every dot-leader row and the vertical `|` stats divider align to exact monospace character columns across macOS/Windows/Linux browsers.
  - [ ] Left ASCII portrait preserves exact silhouette density and `#6b997c`/`#95c0a5` terminal green palette.
  - [ ] All numerical GitHub stats come strictly from live API data (`GITHUB_TOKEN` GraphQL `contributionsCollection` in CI, with documented REST fallback locally — zero fabricated values).

---

### 5.4 SECTION 03 — Automatic Repository Explorer (Approved Option A)

- **Design System (Measured from Image 3 `453x1024`):**
  - Card background: `#080c18`; Border: `1px solid #151922` (`rx="12"`); Primary text: `#e5e9f3`; Secondary muted text: `#9095a0`; Accent blue: `#8294ea`; Constellation node fill: `#152d4d`; Dashed rule/connector: `#2e3341` / `#4a4f5a`.
  - Square language badge icons (`22x22` / `26x26`, `rx="4"`): `Python` (`#3472a5` / `#f8de55`), `TypeScript` (`#3a78c1`), `HTML` (`#c35e4e`), `JavaScript` (`#f0dc63`), `C` (`#3e424b`), `PLpgSQL` (`#152d4d`), plus fallback neutral icon (`#363a3f`) for `Unspecified` / other languages.
- **Two-Part Section 03 Architecture (`Built, shipped, shared`):**
  1. **Part A — Overview Card (`assets/repos_overview.svg`, `viewBox="0 0 988 320"`):**
     - Matches Image 3's `Built, shipped, shared` → `PROJECT CONSTELLATION` / `A universe of work` (or collision-free `PROJECT LAUNCH SEQUENCE`) styling: `#080c18` card, uppercase tracked monospace eyebrow, sans heading, dashed divider, orbital/timeline nodes dynamically driven by the top `N` (up to `5`) active non-archived repositories sorted by prominence/recency.
     - Vertical clearance enforced (`>=18px` between every label) so zero text collisions occur.
  2. **Part B — Clickable All-Repository Card Grid (`assets/repos/<repo_slug>.svg`):**
     - Auto-generated SVG card (`viewBox="0 0 480 176"`, `rx="12"`, `#080c18` fill, `#151922` stroke) for **every** public repository owned by `Eshtiaq-a`, wrapped in `<a href="https://github.com/Eshtiaq-a/<repo>"><img src="assets/repos/<repo_slug>.svg" width="48%" alt="..."></a>` inside a clean responsive 2-column README table/grid!
     - **Card Anatomy:**
       - Top row: Square language badge icon (`24x24`) + Repository name (`16px` bold `#e5e9f3`) + right-aligned status pill (`Live` if `homepage` set, `Archived` if archived, `Empty` if `size == 0` — subtle `#152d4d` / `#8294ea`).
       - Middle block (`2` lines max, `12.5px` `#9095a0`): Word-wrapped repository description (or `"No description provided yet."` when null/empty).
       - Dashed divider (`#2e3341`).
       - Bottom metadata footer (`11.5px` monospace `#9ea2ad`): Primary language (`"Unspecified"` if null) · `★ {stars}` · `⑂ {forks}` · right-aligned `Updated MMM YYYY`.
- **Visual Acceptance Criteria (Section 03):**
  - [ ] Every public repository owned by `Eshtiaq-a` appears in the clickable grid without any manual list.
  - [ ] Clicking any card opens its exact GitHub repository URL (`html_url`).
  - [ ] Cards display `name`, `description` (with safe empty fallback), `language` (with safe null fallback), `stars`, and `forks` cleanly with zero overlapping or clipped text.
  - [ ] Newly created public repos appear automatically on the next scheduled or manual workflow run.

---

## 6. Movie Credits Engine — Detailed Technical Specification

### A. Data Collection Pipeline (`src/github_client.py` + `src/credits_builder.py`)

1. **Repository Enumeration:**
   - Fetch `GET /users/Eshtiaq-a/repos?type=owner&per_page=100` following `Link: <...>; rel="next"` pagination until exhausted. Filter strictly to `private == False`.
2. **Branch Enumeration (Decision 01):**
   - For each public repository, fetch `GET /repos/{owner}/{repo}/branches?per_page=100` (paginated).
   - If the repository is empty (`branches == []` or `HTTP 409 Conflict` / `404`), record `0` commits and continue safely.
3. **Branch Commit Traversal:**
   - For each branch `b`, URL-encode branch names (`urllib.parse.quote(b["name"], safe="")` to handle slash branch names like `sub/test-branch` and `vercel/...`) and paginate `GET /repos/{owner}/{repo}/commits?sha={encoded_branch}&per_page=100`.
4. **Deduplication & Chronological Ordering:**
   - Composite deduplication key: **`(repo_id, sha)`** (guaranteeing commits shared across `main` and feature branches appear once while preserving cross-repo uniqueness if two repos ever shared history).
   - Aggregate encountered branch names into `branches: sorted(list[str])` on the unique `CommitRecord`.
   - Identify merge commits via `len(commit["parents"]) > 1` (`is_merge: bool`), preserving them intact in history.
   - Sort chronologically **oldest to newest** by `(committed_at_utc, repo_name.lower(), sha)`.
5. **Missing Metadata Handling:**
   - Fallback chain for date: `commit.committer.date` or `commit.author.date`.
   - Fallback chain for author: `commit.author.name` → `author.login` → `"Eshtiaq Ahmad"` (if GitHub commit record author object is missing).
   - Normalize multi-line commit messages: keep subject line (and optional cleaned body preview if desired, stripped of control characters, truncated cleanly at word boundaries).
6. **Documented GitHub API Limitations & Inaccessible History:**
   - **Private Repositories & Private Branches:** Deliberately excluded; only public repositories and public branches are queried.
   - **Orphaned / Force-Pushed / Rebased Commits:** Commits not reachable from any current public branch head (`refs/heads/*`) are not exposed by `/commits`.
   - **Unmerged Tag-Only Commits:** Commits referenced solely by tags and unreachable from any branch head are excluded unless tag heads are explicitly added later.
   - **Squash-Merged PRs:** Appear as single squashed commits on the target branch unless the source branch still exists publicly.
   - **Rate Limits:** Unauthenticated calls allow `60` REST requests/hour; CI runs use `GITHUB_TOKEN` (`5,000` requests/hour).

### B. Canonical Commit Data Model (`data/commits.json`)

```json
{
  "generated_at": "2026-11-26T16:24:00Z",
  "scope": "all_accessible_public_branches",
  "total_unique_commits": 68,
  "repositories_scanned": 8,
  "branches_scanned": 10,
  "commits": [
    {
      "repo_id": 1130000000,
      "repo_name": "Wrechship",
      "repo_full_name": "Eshtiaq-a/Wrechship",
      "sha": "0123456789abcdef0123456789abcdef01234567",
      "short_sha": "0123456",
      "message": "fix: prevent map rotation from resuming automatically if manually stopped",
      "author": "Eshtiaq_Ah",
      "committed_at": "2026-07-27T20:38:00Z",
      "commit_date": "2026-07-27",
      "commit_url": "https://github.com/Eshtiaq-a/Wrechship/commit/0123456789abcdef0123456789abcdef01234567",
      "branches": ["main"],
      "is_merge": false
    }
  ]
}
```
*(Note: Author email addresses from Git commit metadata are deliberately omitted from `data/commits.json` and rendered assets to protect contributor privacy.)*

### C. Cinematic Credit Script & Animation Mechanics

- **Credit Roll Structure:**
  1. **Opening Sequence (`~140px` height):**
     - `A PRODUCTION BY`
     - `ESHTIAQ AHMAD`
     - `GITHUB CHRONICLES — COMMIT CREDITS`
     - `ALL ACCESSIBLE PUBLIC BRANCHES`
  2. **Body Sequence (Chronological Credit Blocks):**
     - Grouping rule for clean cinematic readability: whenever consecutive commits belong to the same repository, display a prominent centered **`[ REPOSITORY NAME ]`** title card header once per run of commits (or tag each commit block clearly with its repository header when switching repositories), followed by each commit entry:
       - Commit message (wrapped max 2 lines, XML-escaped via `html.escape`)
       - `YYYY-MM-DD  •  Author: <name>` (plus `[merge]` tag if `is_merge`)
  3. **Closing Sequence (`~150px` height):**
     - `FILMED IN DHAKA, BANGLADESH`
     - `CAST: {total_unique_commits} COMMITS · {repo_count} REPOSITORIES · {branch_count} BRANCHES`
     - **`THE END?`**
     - **`THE JOURNEY CONTINUES.`**
- **Seamless Vertical Loop Mathematics:**
  - Let `H_seq` be the exact vertical pixel height of `[Opening + Body + Closing + tail spacer]`.
  - Render `<g id="credits-track">` containing two identical copies of the sequence stacked at `y = 0` and `y = H_seq`, clipped inside `<clipPath id="monitor-screen-clip">` (`x=429, y=132, width=246, height=142`).
  - Animate `transform: translateY(0px)` → `translateY(-{H_seq}px)` linearly (`animation-timing-function: linear; animation-iteration-count: infinite;`).
  - Duration calculated from constant scroll velocity `v = 22 px/sec` (`duration = round(H_seq / 22.0, 2)` seconds), ensuring consistent, calm, readable cinema pacing regardless of commit count.

### D. Experimental SVG-First Rendering & Animated GIF Fallback (Decision 04)

1. **Experimental Primary Renderer (`src/svg_workspace.py`):**
   - Produces self-contained `assets/workspace.svg` using pure SVG `<style>` `@keyframes` + `<clipPath>` as an **experimental first choice** (zero `<script>`, zero `<foreignObject>`, zero external fonts).
   - **Phase 1 Sample Data Discipline:** During the initial Phase 1 visual milestone, `svg_workspace.py` renders from an explicitly named, clearly labelled sample fixture (`data/sample_commits.json`, e.g., `"sample_data": true` banner/comment in fixture) before any live GitHub API integration begins.
2. **GitHub Live Verification Protocol (Mandatory Gate Before Relying on SVG):**
   - With explicit user approval, test the Phase 1 sample `assets/workspace.svg` inside an actual GitHub `README.md` (`https://github.com/Eshtiaq-a`) via Camo `<img>`.
   - Inspect in desktop Chrome, Safari, Firefox, and mobile view to verify: (a) Camo preserves `@keyframes` inside `image/svg+xml`, (b) upward scroll runs continuously and loops seamlessly without stalling or jumping, (c) text stays crisp inside the monitor bezel without clipping, and (d) rendering performance is smooth.
   - **Do not rely on animated SVG for downstream phases until this live GitHub test passes.**
3. **GIF Fallback Renderer (`src/gif_workspace.py` — Triggered If SVG Test Fails):**
   - If Camo or browser rendering blocks, clips, stalls, or degrades animated SVG, switch Section 01 cleanly to `assets/workspace.gif` rendering the exact same pixel-art scene and credit sequence inside the `246x142` external monitor dirty rectangle (`top=132, left=429`, `988x504` palette <= 64 colors, `12–15 fps`, infinite loop `0`, targeting **`< 1.5 MB`** well below Camo's ~5 MB cap).

### E. Performance & Scalability Budget

| Scaling Dimension | Target Limit / Handling Strategy |
|---|---|
| **Large Commit History** | Full history preserved in `data/commits.json`. If rendered SVG exceeds `350 KB` or `H_seq > 14,000 px` (~300+ commits), apply configurable credit-roll windowing (keep earliest origin milestone commits + grouped summary of middle commits + full recent commits, or reduce per-entry vertical density) so SVG stays `< 450 KB` and GIF stays `< 3.5 MB`. |
| **SVG DOM & Memory** | Stream/build SVG elements with Python string templates/lists (`"".join(...)`) in `< 100ms` and `< 30 MB` peak RAM. |
| **API Rate Limit Budget** | Current `8` repos / `10` branches consumes only `~19` REST calls + `1` GraphQL call (`~0.4%` of `5,000 req/hr` `GITHUB_TOKEN` budget). Add ETag/conditional caching or incremental branch-SHA cache if repo count grows above `100+`. |
| **Generation Time** | Target `< 5s` total for SVG pipeline (network + render + validation); `< 15s` if GIF fallback is active. |

---

## 7. Repository Explorer — Detailed Technical Specification (`src/repos_builder.py` + `src/svg_explorer.py`)

1. **Auto-Discovery:** Fetch all public repositories via `GET /users/Eshtiaq-a/repos?type=owner&per_page=100` (paginated), filtering `private == False`. Zero hardcoded repository names anywhere in Python or config.
2. **Metadata Extraction (`data/repos.json`):**
   - `id`, `name`, `full_name`, `html_url`, `homepage`, `description`, `language`, `stargazers_count`, `forks_count`, `archived`, `fork`, `size`, `pushed_at`, `created_at`, `topics`.
3. **Documented Sorting Strategy:**
   - Configurable ordering in `config/profile.json` (`sort_order: "stars_then_pushed"`):
     1. Non-archived repositories before archived repositories (`archived == False` first).
     2. Non-empty software repositories before profile meta-repo `Eshtiaq-a/Eshtiaq-a` (or sort strictly by stars/activity if configured).
     3. `stargazers_count` descending.
     4. `pushed_at` descending (ISO-8601 UTC).
     5. `name.lower()` ascending.
4. **Edge-Case Handling:**
   - **Empty description (`None` or `""`):** Display `"No description provided yet."` in muted `#9095a0`.
   - **Missing primary language (`None`):** Display `"Unspecified"` with neutral dark badge `#363a3f`.
   - **Empty repository (`size == 0`, e.g., `Eshtiaq-a` before first push):** Tag pill `"Empty"` (or omit if `exclude_empty_profile_repo` is enabled after first commit it automatically ceases to be empty!).
   - **Archived repositories (`archived == True`):** Retained in explorer with a subtle `"Archived"` badge (`#585d69`) and ranked below active repositories.
   - **Long descriptions / long repo names:** Word-wrapped cleanly across max 2 lines on SVG cards with clean ellipsis `"..."` only at word boundary, never slicing mid-word inside overlapping elements.

---

## 8. Automation, Validation & Security Architecture

### 8.1 Modular File Structure

```text
Eshtiaq-a/
├── .github/workflows/update-profile.yml
├── assets/
│   ├── ascii_portrait.txt          # Deterministic ASCII portrait matching Image 2
│   ├── workspace.svg               # Section 01 (primary animated SVG)
│   ├── workspace.gif               # Optional fallback only if GIF mode enabled
│   ├── neofetch.svg                # Section 02 terminal SVG
│   ├── repos_overview.svg          # Section 03 overview SVG (Built, shipped, shared)
│   └── repos/<repo_slug>.svg       # Section 03 auto-generated clickable project cards
├── config/profile.json             # Optional decorative flags, role/contact overrides, sort prefs
├── data/
│   ├── commits.json
│   ├── profile_data.json
│   ├── repos.json
│   └── sample_commits.json         # Clearly labelled Phase 1 sample-data fixture only
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── github_client.py            # Paginated REST + GraphQL client, 409 handling, rate-limit retries
│   ├── weather_client.py           # Optional Open-Meteo Dhaka client (no-op when disabled)
│   ├── credits_builder.py          # All-branch commit fetch, (repo_id, sha) dedup, chronological sort
│   ├── stats_builder.py            # Uptime, language breakdown, GraphQL calendar/streak math
│   ├── repos_builder.py            # Dynamic repo discovery, sorting, empty/archived normalization
│   ├── gif_workspace.py            # Section 01 optimized animated GIF fallback renderer
│   ├── svg_workspace.py            # Section 01 experimental animated SVG renderer
│   ├── svg_neofetch.py             # Section 02 SVG renderer
│   ├── svg_explorer.py             # Section 03 overview + per-repo card SVG renderers
│   ├── readme_builder.py           # Sanitized 3-section README.md generator
│   ├── validators.py               # JSON schema, dedup/sort invariants, XML/SVG safety checks
│   └── main.py                     # CLI (`--dry-run`, `--offline`, `--sample-data`, `--gif-fallback`)
├── tests/                          # Unit + integration tests (mocked APIs & SVG/JSON validators)
├── PROJECT_PLAN.md
└── README.md
```

### 8.2 GitHub Actions Workflow (`.github/workflows/update-profile.yml`)

- **Triggers:**
  - `schedule`: `cron: "23 */6 * * *"` (every 6 hours, jittered off top-of-hour).
  - `workflow_dispatch`: Manual execution on demand.
  - `push` to `main` limited to `paths: ["src/**", "config/**", ".github/workflows/**"]`.
- **Least-Privilege Security Controls:**
  - Top-level `permissions: contents: write` only (no `issues`, `pull-requests`, `packages`, or org permissions).
  - Pin official actions (`actions/checkout@v4`, `actions/setup-python@v5`) and set `timeout-minutes: 10`.
  - Pass `${{ secrets.GITHUB_TOKEN }}` exclusively via `env: GITHUB_TOKEN` — never echoed, never embedded in JSON/SVG/logs.
  - Query **public data only** (`type=owner` + `private == False` check); never request private repos or sensitive contributor emails.
- **Safety Gates Before Commit:**
  - Pipeline writes to staging buffers/validates via `src/validators.py` before overwriting `assets/` or `README.md`.
  - If critical GitHub API calls fail, workflow exits non-zero **without modifying** existing live profile files.
  - Stale cleanup: delete orphaned `assets/repos/*.svg` files when a repository is deleted or made private, keeping `assets/repos/` strictly synchronized with live public repos.
  - Commit only when `git status --porcelain` shows actual changes, using commit message `chore: update profile data and SVGs [skip ci]`.

### 8.3 Injection, Escaping & Validation Controls

- **SVG/XML Safety:** All user-controlled strings (`repo_name`, `description`, `commit_message`, `author`, `bio`) pass through strict control-character stripping + `html.escape(text, quote=True)`. Generated SVGs are parsed with `xml.etree.ElementTree.fromstring()` and asserted to contain **zero** `<script>`, `<foreignObject>`, `onload=`, `onclick=`, or external `http://` asset refs.
- **Markdown/HTML Sanitization:** Repository URLs validated against `https://github.com/` prefix; `alt` attributes and link text escaped so malformed repo descriptions cannot break README layout or inject unexpected HTML tags.

---

## 9. Testing Strategy & Phased Implementation Roadmap

### 9.1 Automated Test Suite (`unittest` / `pytest`)

- `test_github_client.py`: Multi-page `Link` pagination, URL-encoded branch names (`sub/test-branch`), `HTTP 409` empty repository handling, `403`/`429` retry/backoff handling.
- `test_credits_builder.py`: Multi-branch deduplication via `(repo_id, sha)`, branch-list aggregation, merge-commit retention, chronological oldest-to-newest sorting, opening/closing sequences (`THE END? — THE JOURNEY CONTINUES.`), zero email leakage.
- `test_stats_builder.py`: Uptime calculation, GraphQL streak/active-day computation, REST fallback when `GITHUB_TOKEN` is absent.
- `test_repos_builder.py`: Auto-discovery of newly added mock repos, archived sorting, empty description/language fallbacks, stale SVG card cleanup.
- `test_workspace_svg.py`: Phase 1 sample-data rendering, `@keyframes` + `<clipPath>` invariants, special-character escaping, and GIF fallback smoke checks.
- `test_validators_and_svgs.py`: XML well-formedness, `<clipPath>` & `@keyframes` presence, zero `<script>`/`<foreignObject>`, SVG byte-size limits, special-character commit escaping (`<>&"'`), and GIF fallback validation if enabled.

### 9.2 Implementation Phases (Strict Gated Sequence — Awaiting Authorization)

> **Execution Guardrails:**
> - **Do NOT** execute nested Git cleanup or any destructive command without explicit human authorization.
> - **Do NOT** begin Phase 1 implementation until explicit approval of Phase 0 + Phase 1 is granted.
> - **Visual Approval Gate:** After Phase 1 delivers the pixel-art workspace + movie-credit monitor on clearly labelled sample data and verifies GitHub rendering, **STOP** and obtain explicit user visual approval before starting Phase 2 (full GitHub data integration).

| Phase | Deliverables & Scope | Exit & Approval Gate |
|---|---|---|
| **Phase 0: Authorized Git Cleanup & Baseline Lock** *(Blocked until explicit approval)* | With explicit user permission, verify inner `Eshtiaq-a/` contains zero non-Git files/objects, remove the duplicate empty inner repository, and establish `/Users/eshtiaqahmad/git profile/Eshtiaq-a` as the single clean project root + baseline `config/profile.json`. | User explicitly authorizes cleanup commands & Phase 1 start; single clean root confirmed (`git status`). |
| **Phase 1: First Visual Milestone — Pixel-Art Workspace (MacBook + External Monitor Movie Credits, Sample Data)** | Implement `src/config.py`, `src/validators.py`, clearly labelled sample fixture `data/sample_commits.json` (`"is_sample_data": true`), `src/svg_workspace.py` (MacBook with subtle desktop/terminal + visible cable + larger central external monitor with cinematic movie credits, 1–2 plants, male-only/no-female rule, matching `ref1.jpg` & Section 5.2), `src/gif_workspace.py` fallback if needed, and unit/XML tests (`tests/test_workspace_svg.py`). Verify animated SVG rendering on actual GitHub `README.md` via Camo `<img>`. | **Visual Quality Gate:**<br>1. All Section 5.2 Visual Acceptance Criteria met (MacBook + connected larger external monitor, zero female characters, 1–2 subtle plants, zero collisions).<br>2. Movie credits scroll smoothly upward & loop seamlessly exclusively on the external monitor.<br>3. Live GitHub Camo rendering verified (SVG confirmed or GIF fallback activated).<br>4. **Explicit human visual approval obtained before Phase 2.** |
| **Phase 2: Full GitHub Data Integration & Multi-Branch Credits** *(Blocked until Phase 1 visual sign-off)* | Implement `src/github_client.py`, `src/credits_builder.py` (all accessible public branches, `(repo_id, sha)` deduplication, chronological sorting, merge handling, 409 empty-repo handling), `src/stats_builder.py`, `src/repos_builder.py`, optional `src/weather_client.py`, and full mocked/live unit tests; wire real `data/commits.json` into Section 01 replacing sample fixture. | All Phase 2 unit tests pass; live public API generates validated `data/*.json` and real multi-branch movie credits. |
| **Phase 3: Section 02 — Neofetch Developer Terminal** | Implement `src/svg_neofetch.py` + `assets/ascii_portrait.txt` + renderer/alignment tests matching Reference Image 2 & Section 5.3 criteria, driven by live `data/profile_data.json`. | Exact column/dot-leader alignment, palette match to Image 2, and visual sign-off verified. |
| **Phase 4: Section 03 — Automatic Repository Explorer (`Option A`) & README Assembly** | Implement `src/svg_explorer.py` (`assets/repos_overview.svg` + clickable per-repo `assets/repos/*.svg` cards) + `src/readme_builder.py` + stale-card pruning + end-to-end integration tests. | All public repos rendered & clickable, zero text collision, empty/archived/missing-language edge cases verified. |
| **Phase 5: GitHub Actions Automation, Security & Live Verification** | Add `.github/workflows/update-profile.yml` (`permissions: contents: write`, pinned actions, validation gates, `[skip ci]`), run full test suite, and perform final live profile + `workflow_dispatch` verification after user-approved push. | Full test suite passes; automated workflow updates live profile cleanly on GitHub. |
