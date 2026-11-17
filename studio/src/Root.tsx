import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Long, Short, StoryProps} from './Story';

const demo: StoryProps = {
  fps: 30,
  audio: 'demo/voice.mp3',
  title: 'Demo',
  words: [{w: 'Demo', s: 0, e: 1}],
  scenes: [{start: 0, end: 3, bg: 'demo/bg.png', chars: [{src: 'demo/girl.png', pos: 'giua', motion: 'nhun'}]}],
};

const calc: CalculateMetadataFunction<StoryProps> = ({props}) => ({
  fps: props.fps,
  durationInFrames: Math.max(1, Math.ceil(props.scenes[props.scenes.length - 1].end * props.fps)),
});

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Long" component={Long} width={1920} height={1080} fps={30} durationInFrames={90}
      defaultProps={demo} calculateMetadata={calc} />
    <Composition id="Short" component={Short} width={1080} height={1920} fps={30} durationInFrames={90}
      defaultProps={demo} calculateMetadata={calc} />
  </>
);
