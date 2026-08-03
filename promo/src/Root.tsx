import { Composition } from "remotion";
import { DagricPromo } from "./DagricPromo";
import { DagricShort } from "./DagricShort";
import { InstallWalkthrough } from "./InstallWalkthrough";
import { DagricLooks, DAGRIC_LOOKS_FRAMES } from "./DagricLooks";

/**
 * Four pieces, four jobs. Kept separate rather than cutting one master down:
 * the vertical is not a crop of the horizontal (see the note at the top of
 * DagricShort.tsx), and the walkthrough answers a question the promo never
 * asks.
 *
 *   DagricPromo         1920x1080  53s  "why would I want this"   — features page
 *   InstallWalkthrough  1920x1080  47s  "how hard is the install" — download page
 *   DagricShort         1080x1920  28s  the feed                  — social
 *   DagricLooks         1920x1080  34s  "how much do I get"       — homepage Looks section
 *
 * DagricLooks overlaps DagricPromo's own `Looks` scene on subject and not on
 * job: the promo scene is one beat inside a feature reel and shows four of the
 * seven layouts, this one is the section piece for /#looks and shows all
 * seven. It is a standalone composition rather than a splice because inserting
 * 1020 frames into DagricPromo would shift every downstream `from` and both
 * the 1600 below and the arithmetic line at the end of this comment.
 *
 * durationInFrames must equal the last Sequence's `from + durationInFrames` in
 * each file, or the video ends mid-scene or holds on black. Cross-check when
 * editing: DagricPromo 1470+130=1600, InstallWalkthrough 1302+120=1422,
 * DagricShort 740+100=840, DagricLooks 903+117=1020.
 *
 * DagricLooks exports that last sum as DAGRIC_LOOKS_FRAMES and builds it from
 * the same constants its Sequences use, so its two numbers cannot disagree —
 * the other three still rely on somebody re-doing the addition by hand.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DagricPromo"
        component={DagricPromo}
        durationInFrames={1600}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="InstallWalkthrough"
        component={InstallWalkthrough}
        durationInFrames={1422}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="DagricLooks"
        component={DagricLooks}
        durationInFrames={DAGRIC_LOOKS_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="DagricShort"
        component={DagricShort}
        durationInFrames={840}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
