import { Composition } from "remotion";
import { DagricPromo } from "./DagricPromo";
import { DagricShort } from "./DagricShort";
import { InstallWalkthrough } from "./InstallWalkthrough";

/**
 * Three pieces, three jobs. Kept separate rather than cutting one master down:
 * the vertical is not a crop of the horizontal (see the note at the top of
 * DagricShort.tsx), and the walkthrough answers a question the promo never
 * asks.
 *
 *   DagricPromo         1920x1080  53s  "why would I want this"   — features page
 *   InstallWalkthrough  1920x1080  47s  "how hard is the install" — download page
 *   DagricShort         1080x1920  28s  the feed                  — social
 *
 * durationInFrames must equal the last Sequence's `from + durationInFrames` in
 * each file, or the video ends mid-scene or holds on black. Cross-check when
 * editing: DagricPromo 1470+130=1600, InstallWalkthrough 1302+120=1422,
 * DagricShort 740+100=840.
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
