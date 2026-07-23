import { Composition } from "remotion";
import { DagricPromo } from "./DagricPromo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="DagricPromo"
      component={DagricPromo}
      durationInFrames={1420}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
