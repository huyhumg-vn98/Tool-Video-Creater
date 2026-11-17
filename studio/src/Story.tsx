// Bộ dựng phim ghép lớp — dùng chung cho 16:9 (Long) và 9:16 (Short).
// Dữ liệu vào (props) do agent Dựng phim tạo từ storyboard + timing.
import React from 'react';
import {
  AbsoluteFill, Audio, Img, Sequence, continueRender, delayRender,
  interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';

export type Word = {w: string; s: number; e: number};
export type Motion = 'dung' | 'truot_vao' | 'nhun' | 'rung' | 'lat';
export type Char = {
  src: string; pos: 'trai' | 'giua' | 'phai'; motion: Motion; h?: number; flip?: boolean;
  talk?: boolean;   // nhân vật đang nói → nhép miệng + nhún theo từng từ
  mouth?: string;   // ảnh cùng tư thế, miệng mở (đã căn khớp với src)
  blink?: string;   // ảnh cùng tư thế, nhắm mắt
};
export type Scene = {
  start: number; end: number; bg: string; chars: Char[];
  emphasis?: string; cam?: 'in' | 'out' | 'left' | 'right';
};
export type StoryProps = {fps: number; audio: string; scenes: Scene[]; words: Word[]; title?: string};

// ---------- font chữ nhấn (Anton có đủ dấu tiếng Việt) ----------
const anton = new FontFace('Anton', `url(${staticFile('fonts/Anton-Regular.ttf')})`);
const fontHandle = delayRender('Tải font Anton');
anton.load().then((f) => {
  document.fonts.add(f);
  continueRender(fontHandle);
});

const SUB_FONT = 'Arial, Helvetica, sans-serif';
const CAMS = ['in', 'right', 'out', 'left'] as const;

// ---------- nhân vật ----------
// hash nhỏ để mỗi nhân vật chớp mắt/lắc lư lệch nhịp nhau
const seed = (s: string) => [...s].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) % 9973, 7);

const CharView: React.FC<{c: Char; t0: number; words: Word[]}> = ({c, t0, words}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = t0 + frame / fps;           // giây tuyệt đối trong video (khớp mốc từng từ)
  const sd = seed(c.src);
  let tx = 0, rot = 0, sx = 1, sy = 1, ty = 0;

  // --- đang nói: tìm từ hiện tại (tiếng Việt: 1 từ ≈ 1 âm tiết) ---
  let open = false;
  if (c.talk) {
    const w = words.find((x) => t >= x.s && t < x.e);
    if (w) {
      const k = (t - w.s) / Math.max(0.06, w.e - w.s);
      open = k < 0.72;                    // mở ~70% thời lượng âm tiết, khép lại giữa các tiếng
      const kick = Math.exp(-(t - w.s) * 14);
      sy *= 1 + 0.025 * kick;             // nhún nhẹ mỗi tiếng
      ty -= 0.6 * kick;
    }
  }
  // --- chớp mắt: mỗi 2.8–4.6s, dài 0.13s ---
  const period = 2.8 + (sd % 19) / 10;
  const blinking = !!c.blink && !open && ((t + sd / 100) % period) < 0.13;
  // --- lắc lư rất nhẹ khi đứng yên ---
  rot += Math.sin(t * 1.3 + sd) * 0.6;
  if (c.motion === 'truot_vao') {
    const sp = spring({frame, fps, config: {damping: 14}});
    tx = interpolate(sp, [0, 1], [c.pos === 'trai' ? -160 : 160, 0]);
  }
  if (c.motion === 'nhun') {
    const b = spring({frame, fps, config: {damping: 7, stiffness: 170}});
    sy = interpolate(b, [0, 1], [0.7, 1]);
    sx = interpolate(b, [0, 1], [1.2, 1]);
  }
  if (c.motion === 'rung') {
    const k = Math.max(0, 1 - frame / (0.7 * fps));
    tx = Math.sin(frame * 1.9) * 7 * k;
    rot = Math.sin(frame * 2.4) * 4 * k;
  }
  if (c.motion === 'lat') {
    sx = interpolate(spring({frame, fps, config: {damping: 11}}), [0, 1], [-1, 1]);
  }
  const breath = 1 + Math.sin(t * Math.PI * 0.55 + sd) * 0.014; // "thở"
  const left = {trai: 24, giua: 50, phai: 76}[c.pos];
  // Ảnh miệng mở / nhắm mắt đã được căn khớp cùng khung với ảnh gốc → chồng lên, chỉ bật/tắt độ mờ
  const over = (src: string, show: boolean) => (
    <Img src={staticFile(src)} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', opacity: show ? 1 : 0}} />
  );
  return (
    <div style={{
      position: 'absolute', bottom: '3%', left: `${left}%`, height: `${c.h ?? 64}%`,
      transformOrigin: 'bottom center',
      transform: `translateX(-50%) translateX(${tx}%) translateY(${ty}%) rotate(${rot}deg) scale(${sx * (c.flip ? -1 : 1)}, ${sy * breath})`,
    }}>
      <Img src={staticFile(c.src)} style={{height: '100%', display: 'block', opacity: (open && c.mouth) || blinking ? 0 : 1}} />
      {c.mouth ? over(c.mouth, open) : null}
      {c.blink ? over(c.blink, blinking) : null}
    </div>
  );
};

// ---------- chữ nhấn ----------
const Emphasis: React.FC<{text: string; size: number}> = ({text, size}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame > 2.6 * fps) return null;
  const s = spring({frame: frame - 4, fps, config: {damping: 9}});
  return (
    <div style={{
      position: 'absolute', top: '6%', width: '100%', textAlign: 'center',
      fontFamily: 'Anton', fontSize: size, color: '#E3201B', letterSpacing: 2,
      WebkitTextStroke: `${Math.round(size / 9)}px white`, paintOrder: 'stroke fill',
      transform: `scale(${s})`, textTransform: 'uppercase',
    }}>{text}</div>
  );
};

// ---------- 1 cảnh (vẽ trong khung bất kỳ, đơn vị %) ----------
const SceneView: React.FC<{scene: Scene; idx: number; emphSize: number; words: Word[]}> = ({scene, idx, emphSize, words}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = Math.min(1, frame / Math.max(1, (scene.end - scene.start) * fps));
  const cam = scene.cam ?? CAMS[idx % 4];
  const z = cam === 'in' ? 1 + 0.08 * p : cam === 'out' ? 1.08 - 0.08 * p : 1.08;
  const tx = cam === 'right' ? interpolate(p, [0, 1], [-3, 3]) : cam === 'left' ? interpolate(p, [0, 1], [3, -3]) : 0;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img src={staticFile(scene.bg)} style={{
        width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z}) translateX(${tx}%)`,
      }} />
      {scene.chars.map((c, i) => <CharView key={i} c={c} t0={scene.start} words={words} />)}
      {scene.emphasis ? <Emphasis text={scene.emphasis} size={emphSize} /> : null}
    </AbsoluteFill>
  );
};

// ---------- phụ đề theo từng từ ----------
function chunk(words: Word[], max: number): Word[][] {
  const out: Word[][] = [];
  let cur: Word[] = [];
  const minLen = Math.min(3, max);
  for (const w of words) {
    cur.push(w);
    const endSentence = /[.!?…]$/.test(w.w);
    const comma = /[,;:]$/.test(w.w) && cur.length >= minLen;
    if (cur.length >= max || endSentence || comma) {
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  // gộp cụm lẻ 1 chữ vào cụm trước (nếu còn chỗ)
  for (let i = out.length - 1; i > 0; i--) {
    if (out[i].length === 1 && out[i - 1].length < max + 2) {
      out[i - 1] = out[i - 1].concat(out[i]);
      out.splice(i, 1);
    }
  }
  return out;
}

const Subtitles: React.FC<{words: Word[]; mode: 'long' | 'short'}> = ({words, mode}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const groups = React.useMemo(() => chunk(words, mode === 'long' ? 8 : 3), [words, mode]);
  const g = groups.find((x, i) => t >= x[0].s && t < (groups[i + 1]?.[0].s ?? x[x.length - 1].e + 0.4));
  if (!g) return null;
  const big = mode === 'short';
  const pop = big ? spring({frame: frame - Math.round(g[0].s * fps), fps, config: {damping: 10, stiffness: 200}}) : 1;
  return (
    <div style={{
      position: 'absolute', left: '5%', width: '90%', textAlign: 'center',
      ...(big ? {top: '79%'} : {bottom: '5%'}),
      fontFamily: SUB_FONT, fontWeight: 900, fontSize: big ? 86 : 60, lineHeight: 1.2,
      color: 'white', WebkitTextStroke: big ? '10px black' : '7px black', paintOrder: 'stroke fill',
      transform: `scale(${interpolate(pop, [0, 1], [0.8, 1])})`,
    }}>
      {g.map((w, i) => {
        const on = t >= w.s && t < w.e + 0.05;
        return <span key={i} style={{color: on ? '#FFE11A' : 'white'}}>{w.w}{i < g.length - 1 ? ' ' : ''}</span>;
      })}
    </div>
  );
};

const scenesSeq = (props: StoryProps, fps: number, render: (s: Scene, i: number) => React.ReactNode) =>
  props.scenes.map((s, i) => (
    <Sequence key={i} from={Math.round(s.start * fps)} durationInFrames={Math.max(1, Math.round((s.end - s.start) * fps))}>
      {render(s, i)}
    </Sequence>
  ));

// ---------- 16:9 ----------
export const Long: React.FC<StoryProps> = (props) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: 'white'}}>
      {scenesSeq(props, fps, (s, i) => <SceneView scene={s} idx={i} emphSize={120} words={props.words} />)}
      <Subtitles words={props.words} mode="long" />
      <Audio src={staticFile(props.audio)} />
    </AbsoluteFill>
  );
};

// ---------- 9:16 ----------
export const Short: React.FC<StoryProps> = (props) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#111'}}>
      {scenesSeq(props, fps, (s, i) => (
        <AbsoluteFill>
          <Img src={staticFile(s.bg)} style={{
            width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(28px) brightness(0.55)', transform: 'scale(1.15)',
          }} />
          <div style={{position: 'absolute', top: '21%', left: 0, width: '100%', aspectRatio: '1 / 1', boxShadow: '0 10px 40px rgba(0,0,0,.5)'}}>
            <SceneView scene={s} idx={i} emphSize={80} words={props.words} />
          </div>
        </AbsoluteFill>
      ))}
      {props.title ? (
        <div style={{
          position: 'absolute', top: '8%', left: '6%', width: '88%', textAlign: 'center',
          fontFamily: 'Anton', fontSize: 92, lineHeight: 1.1, color: 'white',
          WebkitTextStroke: '10px black', paintOrder: 'stroke fill', textTransform: 'uppercase',
        }}>{props.title}</div>
      ) : null}
      <Subtitles words={props.words} mode="short" />
      <Audio src={staticFile(props.audio)} />
    </AbsoluteFill>
  );
};
