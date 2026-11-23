# cronoaudit

[Português](LEIA-ME.md)

**cronoaudit reviews construction and infrastructure schedules.** You give it the XML export of a
schedule, and it tells you what deserves attention. It looks for the failures that produce a
believable wrong number rather than an error message. Examples:
- an activity that started before its predecessor finished;
- an actual date rewritten after the fact;
- a milestone that is one day from its deadline;
- an activity whose two progress percentages disagree.

It works in two ways:

- **With an AI agent**, in a conversation. You ask in plain words ("review this schedule",
  "compare these two versions", "where did the delay come from?") and the agent answers using
  cronoaudit. Use the agent you prefer, or the one your company allows on your computer. This
  guide covers four: Claude Code, GitHub Copilot, Codex (OpenAI) and Grok Build (xAI). Any agent
  that reads the open [Agent Skills](https://agentskills.io) format also works.
- **Without any agent.** One command writes the same report, and nothing leaves your computer.

The numbers never come from the agent. They come from cronoaudit's engine: Python scripts that
run on your computer, read the XML and compute every figure the same way every time. The agent
quotes those figures; it does not invent them.

## What you get

One HTML report that opens in the browser, in the schedule's own language (Portuguese or
English). Every section opens with a short reading written by rules, not by the agent.

**For one delivery:**
- the deadlines first: each milestone against its deadline, with the margin and where its delay
  starts;
- nine integrity checks, network first;
- the S-curve from the file's own data, reconciled to the cent with the tool's own figures;
- productivity and trend by resource;
- fourteen network-quality metrics;
- Earned Schedule and the next weeks;
- forensics that name where each milestone's delay entered.

**For two versions of the same schedule, in the order you read them:**
1. deadlines;
2. whether the measurement can be trusted;
3. what the plan changed;
4. progress;
5. float and critical path;
6. network quality;
7. a list of what to ask the contractor, one item per piece of evidence.

## Before you start

You need three things:

1. **A computer with Windows, macOS or Linux.** This guide shows Windows first, because that
   is where most schedules live.
2. **The schedule as XML.** In MS Project: **File → Save As → XML Format (\*.xml)**. That is
   Project's own format; nothing cronoaudit needs is lost. Save it in a folder of its own.
3. **Optional: an AI agent.** Only if you want the conversation. Each agent needs an account
   with its provider; check which plan includes it, and check your company's policy before
   using one with a company schedule (see [Where your data goes](#where-your-data-goes)).

You do not need to know programming. You will copy and paste a few commands.

### How to open PowerShell (Windows)

1. Press the Windows key.
2. Type `PowerShell`.
3. Click **Windows PowerShell**.

A window with a blinking cursor opens. Paste a command there with a right click, and run it
with Enter. Use this window, not "Command Prompt" (cmd): the commands below are for PowerShell.

On macOS, open **Terminal** instead (Applications → Utilities).

## Step 1: install cronoaudit

One command installs cronoaudit for all the agents at once, and for use without an agent.

**Windows (PowerShell):**

```
irm https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.ps1 | iex
```

**macOS / Linux (Terminal):**

```
curl -fsSL https://raw.githubusercontent.com/Holiv/cronoaudit/main/install.sh | bash
```

What you should see at the end: **`cronoaudit 0.8.0 is installed`**.

About Python: cronoaudit needs Python 3.9 or later and nothing else. On Windows, if your
computer has no Python, the installer brings its own copy from python.org, used only by
cronoaudit, with no administrator rights. On macOS and Linux, Python is usually already there.

To update later, run the same command again.

## Step 2: install an agent (skip this if you will not use one)

Pick one. Each block is the provider's official command, as of November 2026. After
installing, close PowerShell and open a new one, so the new command is found.

### Claude Code (Anthropic)

```
irm https://claude.ai/install.ps1 | iex
```

macOS / Linux: `curl -fsSL https://claude.ai/install.sh | bash`. Start it with `claude` and
follow the sign-in. Official guide: [code.claude.com](https://code.claude.com/docs/en/setup).

### GitHub Copilot CLI

```
winget install GitHub.Copilot
```

Start it with `copilot` and sign in with your GitHub account. It needs a Copilot plan. If your
Copilot comes from your company, the company decides whether the CLI is enabled. Official
guide, with the macOS and Linux options:
[docs.github.com](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli).

### Codex (OpenAI)

```
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

macOS / Linux: `curl -fsSL https://chatgpt.com/codex/install.sh | sh`. Start it with `codex`
and sign in with your ChatGPT account. Official guide:
[github.com/openai/codex](https://github.com/openai/codex).

### Grok Build (xAI)

```
irm https://x.ai/cli/install.ps1 | iex
```

macOS / Linux: `curl -fsSL https://x.ai/cli/install.sh | bash`. Start it with `grok` and sign
in. Official guide: [docs.x.ai](https://docs.x.ai/build/overview).

### Does the agent see cronoaudit?

All four read the skill folder the installer created (`.agents\skills` in your user folder;
Claude Code reads `.claude\skills`, which the installer also fills). To check, start the agent
and ask *"what skills do you have?"*. cronoaudit should be in the answer. In Copilot you can
also type `/skills list`; in Grok, `/skills`.

## Step 3: review a schedule

1. In PowerShell, go to the folder where the XML is. The easiest way: type `cd ` with a space
   after it, drag the folder from Explorer into the window, and press Enter.
2. Start your agent: `claude`, `copilot`, `codex` or `grok`.
3. Write what you want, in your own words. For example:
   - *Review the schedule road-rev04.xml.*
   - *Compare road-rev03.xml with road-rev04.xml and tell me what changed.*
   - *Which milestones are at risk of missing their deadline?*
   - *Write the executive summary and generate the final report.*

The agent runs cronoaudit, reads the results and answers. The report is saved next to the XML,
and you can open it in the browser. You can keep asking about any activity, milestone or figure.

One thing that confuses people: commands that start with `/` (like `/skills`) are typed
**inside** the agent, after you start it. Typed straight into PowerShell, they do nothing.

### What a conversation looks like

From a test on the fictitious road project that ships with cronoaudit ([`examples/`](examples/)):

> **You:** Compare rev03 and rev04 and tell me what changed, by topic.
>
> **Agent:** The project finish moved 21 days, from 04/10/2027 to 25/10/2027. Before the
> progress figure, three things need an answer from the contractor: the actual finish of row 29
> was rewritten and now equals the baseline date; row 119, at 100%, was removed, taking its
> earned value with it; and the baseline of row 132 moved. The delay of the viaduct milestone
> starts at row 148 and grows at row 157, whose duration went from 12 to 20 days…

Every figure in that answer comes from the engine's files. The agent also points out when a
rule-built reading does not fit the data, and shows the numbers.

## Without any agent

Run the engine yourself. Nothing leaves your computer:

```
python "$env:USERPROFILE\.claude\skills\cronoaudit\scripts\review.py" "C:\path\to\schedule.xml"
```

Two files, previous first, give the comparison report. On macOS and Linux, use `python3` and
`~/.claude/skills/cronoaudit/scripts/review.py`.

On Windows, use `python` (or `py`), not `python3`: there `python3` is often a shortcut to the
Microsoft Store that runs nothing.

## Where your data goes

- **The engine runs on your computer and sends nothing.** It never touches the network.
- **The installer downloads** this repository from GitHub and, on Windows only if needed, Python
  from python.org. Nothing else.
- **The agent is different.** What an agent reads (the XML, the report, your questions) goes to
  its provider, under the terms of your account or your company's. Check the company's policy
  before using an agent with a contract schedule.
- **If the policy says no agent,** use cronoaudit without one: same report, no conversation.

### Secret mode (experimental)

For when you want the conversation, but the names, values and dates should stay on your
computer. You run one command yourself:

```
python "$env:USERPROFILE\.claude\skills\cronoaudit\scripts\review.py" "C:\path\to\schedule.xml" --secret
```

cronoaudit analyses the real file on your computer and writes a coded copy in a separate folder:
- activity names become codes like `T·3fa91c`;
- dates become day counts like `D+0412`;
- money is multiplied by a secret factor.

Durations, percentages, indices and row numbers stay real, so the analysis still makes sense.
You open the agent in that folder, and it reads only the coded copy. When you ask for the final
report, cronoaudit decodes it on your computer and opens it with the real names.

What it does and does not do:
- In Claude Code, the folder also carries rules that keep the agent inside it. Other agents
  receive the same rules as written instructions.
- The codes do not make the schedule anonymous: its structure, durations and row numbers stay
  readable.
- It does not replace your company's policy on AI services.

Tested on Windows with Claude Code on 22/11/2026, and on a real 6,484-task schedule: no real
name, date or value reached the coded copy.

## If something goes wrong

| What you see | What to do |
|---|---|
| *'irm' is not recognized* | You are in Command Prompt (cmd). Open PowerShell (see above). |
| *python is not recognized* | Run the cronoaudit installer again; on Windows it brings its own Python. Or install Python from python.org and tick **Add python.exe to PATH**. |
| The agent's command (`claude`, `copilot`…) is not found | Close PowerShell and open a new one. |
| The agent does not know cronoaudit | Close the agent and start it again. In Copilot, `/skills reload`. Check with *"what skills do you have?"*. |
| `/cronoaudit` does nothing | Commands with `/` work only inside the agent, not in PowerShell. You can also just ask in words. |

## More

- **The whole process, step by step:**
  [`skills/cronoaudit/references/usage.md`](skills/cronoaudit/references/usage.md).
- **Manual**, fourteen chapters, from concepts to a glossary: Português
  [`docs/manual/manual-pt.pdf`](docs/manual/manual-pt.pdf), English
  [`docs/manual/manual-en.pdf`](docs/manual/manual-en.pdf).
- **MS Project add-in (Windows, beta).** Buttons in Project that export the open schedule and
  start the analysis. A shortcut, not a requirement: [`msproject/`](msproject/).
- **A fictitious example** to try first, with the list of what was planted in it:
  [`examples/`](examples/).

### Other ways to install

| Route | Command |
|---|---|
| Any Agent Skills client | `npx skills add Holiv/cronoaudit -g` |
| Claude Code, as a plugin | `/plugin marketplace add Holiv/cronoaudit`, then `/plugin install cronoaudit@cronoaudit` |
| Codex | `$skill-installer https://github.com/Holiv/cronoaudit` |
| A team, through the project | `git clone https://github.com/Holiv/cronoaudit .agents/skills/cronoaudit` inside the project |

Where the installer puts it: `.claude/skills/cronoaudit` and `.agents/skills/cronoaudit` in
your user folder. On macOS and Linux, `--only claude` or `--only agents` chooses one.

Installer options on Windows are set in the same PowerShell window, before the command:

| Option | Command |
|---|---|
| Never download Python; stop if none is found | `$env:CRONOAUDIT_NO_PYTHON="1"` |
| Use the bundled Python even if the computer has one | `$env:CRONOAUDIT_EMBED_PYTHON="1"` |
| Install from another branch | `$env:CRONOAUDIT_REF="branch-name"` |

### What it does not do

It does not read Primavera P6. It does not produce a contractual delay claim: the forensics
show the mechanism, and a claim needs contemporaneous records and a formal method. It does not
certify against DCMA: the fourteen metrics are an implementation, labelled as such. It never
invents a number the file did not carry, and it marks every claim as `measured`, `inferred` or
`reported`.

### Check the tool

`python skills/cronoaudit/scripts/test_checks.py`, from a copy of this repository. Every check
must fire on the positive fixture and stay silent on the negative one.

### Provenance

Written from a documented, generic method, not ported from any application's source, and
measured on a real 6,484-task programme with 107 calendars. Numbers of scale stay; identities
go: no employer, contractor, contract, chainage, person or value appears in this repository.

### Licence

Apache 2.0. © 2026 Helton da Silva de Oliveira.
