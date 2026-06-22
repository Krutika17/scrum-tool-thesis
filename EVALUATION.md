# Evaluation Walkthrough and Questionnaire

This document describes how to run a task-based walkthrough of the CLI Scrum prototype with a participant, followed by a System Usability Scale (SUS) questionnaire. The walkthrough evaluates the command-line interface. The Mattermost chat layer is a proof of concept and is shown only as a short demonstration, not as part of the scored tasks.

---

## Facilitator setup (before each session)

1. Start the local Focalboard instance:

   docker compose up -d

   Open the board in a browser so the participant can see the visual workspace:
   http://localhost:8000

2. Refresh the access token so the session does not break partway through:

   ./fb_token.sh

3. Reset the board to a known starting state so every participant begins from the same point:

   ./fb_reset.py            # shows what will change (dry run)
   ./fb_reset.py --apply    # performs the reset

4. Confirm the prototype responds:

   ./fb list

If the participant logs should be kept separate, archive `logs/actions.jsonl` between sessions and let the prototype create a fresh one.

---

## Participant briefing

Explain the setting in one or two sentences: the participant is acting as a member of a student project team using short terminal commands to manage a Scrum board. The board is open in the browser and updates after each command. Ask the participant to think aloud and to attempt each task without step-by-step help, so that the walkthrough reflects real first use.

Card ids are shown in the first column of `./fb list`. Several tasks need a card id, which the participant copies from there.

---

## Tasks

1. Show the current board.

   ./fb list

2. Create a new task for the current sprint.

   ./fb add "Write unit tests for login" --status todo --priority high

3. Find a task by a word in its title.

   ./fb search "login"

4. Move a task into progress.

   ./fb move CARD_ID --status progress

5. Add a short note to a task.

   ./fb note CARD_ID "Started implementation"

6. Mark a task as done.

   ./fb done CARD_ID

7. Raise an impediment for something that is blocking the team.

   ./fb imp "Waiting for test environment access"

8. Show the current impediments.

   ./fb impediments

9. Record a daily standup.

   ./fb standup

10. Resolve the impediment once it is cleared.

    ./fb resolve CARD_ID "Access granted by admin"

11. Generate a short report of the work so far.

    ./fb report summary
    ./fb report activity --last 10

After the tasks, the same actions can be shown briefly through the Mattermost chat commands (for example `/fb list` and `/fb standup`) to illustrate that the prototype is not tied to the terminal. This part is a demonstration and is not scored.

---

## System Usability Scale

Ask the participant to rate each statement from 1 to 5, where 1 means strongly disagree and 5 means strongly agree.

1. I think that I would like to use this tool frequently.
2. I found the tool unnecessarily complex.
3. I thought the tool was easy to use.
4. I think that I would need the support of a technical person to be able to use this tool.
5. I found the various functions in this tool were well integrated.
6. I thought there was too much inconsistency in this tool.
7. I would imagine that most people would learn to use this tool very quickly.
8. I found the tool very cumbersome to use.
9. I felt very confident using the tool.
10. I needed to learn a lot of things before I could get going with this tool.

### Scoring

For the odd-numbered items, subtract 1 from the response. For the even-numbered items, subtract the response from 5. Add the ten adjusted scores, which range from 0 to 40, and multiply by 2.5 to get a final score from 0 to 100.
