# Prepare an experiment release

Kind: how-to.

Use an immutable tag for each experiment and a GitHub Release for its notes.
Create a draft first. This experiment does not publish packages or automatically bump versions.
The checked-in release note is the source of the experiment and companion-post mapping.

1. Write `docs/releases/vMAJOR.MINOR.PATCH.md` with the experiment and reproduction command.
2. Name its companion draft and current publication status.
3. Merge validated changes after the required checks pass.
4. Record the full main commit SHA after its CI run succeeds.
5. Run **Draft Experiment Release** with that tag and SHA.

   ```sh
   gh workflow run draft-release.yml --ref main \
     -f tag=v0.1.0 -f commit=FULL_VALIDATED_COMMIT_SHA
   ```

The workflow reads notes from the selected commit.
It requires successful CI, refuses existing releases and tags, and creates a draft.
It verifies the returned target SHA and checks that the tag is still absent.
Draft releases are visible to repository maintainers, not public readers.

## Publish when the companion post is ready

1. Verify that the draft still targets the intended full SHA.
2. Verify that the tag remains absent.
3. Replace the pending companion-post status with its public URL.
4. Verify that the post links back to this release's tag URL.
5. Publish the GitHub draft only after both artifacts are ready.
6. Verify that the new tag resolves to the recorded commit.

Never move a published experiment tag.
A correction gets a new tag and a note describing what changed.
This repository does not upload packages to PyPI.

## Deploy documentation before the first release

Pages is a living site built from validated main.
The first deployment does not require an experiment tag.

```sh
 gh workflow run docs.yml --ref main
```

A published release also triggers deployment from main, not from the release's historical commit.
The deployment refuses a main commit without successful CI.
Experiment evidence remains available through immutable commit links.
