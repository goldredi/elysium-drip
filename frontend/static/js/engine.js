'use strict';

// ============================================================
// EMOJIREAN ENGINE v3 — encoding, decoding, token management
// Extracted from monolithic HTML for server deployment
// Designed for extensibility: custom languages, new char sets
// ============================================================

const EmojireanEngine = (() => {

// -- EMOJI POOL --
const EMOJI_POOL=[
  '\u{1F98A}','\u{1F43A}','\u{1F981}','\u{1F42F}','\u{1F43B}','\u{1F99D}','\u{1F9A8}','\u{1F9A1}','\u{1F9A6}','\u{1F419}','\u{1F991}','\u{1F980}','\u{1F99E}','\u{1F990}','\u{1F433}','\u{1F40B}',
  '\u{1F42C}','\u{1F988}','\u{1F40A}','\u{1F422}','\u{1F98E}','\u{1F40D}','\u{1F996}','\u{1F995}','\u{1F98B}','\u{1F41D}','\u{1F997}','\u{1F982}','\u{1F99F}','\u{1F43F}\uFE0F','\u{1F994}','\u{1F99C}',
  '\u{1F9A9}','\u{1F99A}','\u{1F985}','\u{1F989}','\u{1F54A}\uFE0F','\u{1F986}','\u{1F9A2}','\u{1F984}','\u{1F409}','\u{1F987}','\u{1F420}','\u{1F421}','\u{1F41F}','\u{1F41B}','\u{1F40C}','\u{1F41C}',
  '\u{1F41E}','\u{1F406}','\u{1F993}','\u{1F98F}','\u{1F99B}','\u{1F418}','\u{1F992}','\u{1F998}','\u{1F999}','\u{1F410}','\u{1F98C}','\u{1F413}','\u{1F9AC}','\u{1F9A5}','\u{1F9AD}',
  '\u{1F344}','\u{1F33A}','\u{1F338}','\u{1F33C}','\u{1F33B}','\u{1F339}','\u{1F337}','\u{1F33F}','\u{1F340}','\u{1F331}','\u{1F332}','\u{1F333}','\u{1F334}','\u{1F335}','\u{1F38B}','\u{1F33E}',
  '\u{1FAB4}','\u{1F343}','\u{1FAB7}','\u{1F490}','\u{1F311}','\u{1F312}','\u{1F313}','\u{1F314}','\u{1F315}','\u{1F316}','\u{1F317}','\u{1F318}','\u{1F341}','\u{1F342}',
  '\u{1F347}','\u{1F348}','\u{1F349}','\u{1F34A}','\u{1F34B}','\u{1F34C}','\u{1F34D}','\u{1F96D}','\u{1F34E}','\u{1F34F}','\u{1F350}','\u{1F351}','\u{1F352}','\u{1F353}','\u{1FAD0}','\u{1F95D}',
  '\u{1F345}','\u{1FAD2}','\u{1F965}','\u{1F951}','\u{1F33D}','\u{1F955}',
  '\u2B50','\u{1F31F}','\u{1F4AB}','\u2728','\u26A1','\u{1F32A}\uFE0F','\u2604\uFE0F','\u{1F308}','\u{1F525}','\u{1F4A5}','\u{1F4A2}','\u{1F4A8}','\u{1FAE7}','\u2744\uFE0F','\u{1F30A}','\u{1F30B}',
  '\u{1F319}','\u{1F324}\uFE0F','\u26C5','\u{1F327}\uFE0F','\u26C8\uFE0F','\u{1F329}\uFE0F','\u{1F328}\uFE0F','\u{1F32B}\uFE0F','\u{1F32C}\uFE0F','\u{1F31D}','\u{1F31B}','\u{1F31C}','\u{1F31E}','\u{1F320}',
  '\u{1F48E}','\u{1F52E}','\u{1F9FF}','\u{1F4A0}','\u{1F537}','\u{1F539}','\u{1FAC2}','\u{1FAD9}','\u{1F9CA}','\u{1F5DD}\uFE0F','\u2694\uFE0F','\u{1F3F9}','\u{1F531}','\u269C\uFE0F','\u{1F6E1}\uFE0F',
  '\u2699\uFE0F','\u{1F529}','\u{1F527}','\u{1F9F2}','\u{1FA9D}','\u{1F512}','\u{1F513}','\u{1F4E1}','\u{1F4BE}','\u{1F4FA}','\u{1F4FB}','\u{1F5A5}\uFE0F','\u{1F4A1}','\u{1F50B}','\u{1F4BF}','\u{1F4C0}',
  '\u{1F4F7}','\u{1F4F8}','\u{1F52C}','\u{1F52D}','\u2697\uFE0F','\u{1F9EA}','\u{1F9EB}','\u{1F9EC}','\u{1F511}','\u{1FA84}','\u{1F3A9}',
  '\u{1F3B8}','\u{1F3BA}','\u{1F3BB}','\u{1F941}','\u{1F3B9}','\u{1F3A4}','\u{1F3A7}','\u{1F3B5}','\u{1F3B6}','\u{1F3BC}','\u{1F3AD}','\u{1F3A8}','\u{1F3AF}','\u{1F3B2}','\u{1F0CF}','\u{1F3B0}',
  '\u{1F3B3}','\u{1F3B1}','\u{1F3AE}','\u{1F386}','\u{1F387}','\u{1F9E8}','\u{1F388}','\u{1F389}','\u{1F38A}','\u{1F380}','\u{1F381}','\u{1F3C6}','\u{1F947}','\u{1F948}','\u{1F949}','\u{1F3C5}',
  '\u{1F396}\uFE0F','\u{1F3AA}','\u{1F3A0}','\u{1F3A1}','\u{1F3A2}',
  '\u{1F534}','\u{1F7E0}','\u{1F7E1}','\u{1F7E2}','\u{1F535}','\u{1F7E3}','\u26AB','\u26AA','\u{1F7E4}','\u{1F536}','\u{1F538}','\u{1F53A}','\u{1F53B}',
  '\u2660\uFE0F','\u2665\uFE0F','\u2666\uFE0F','\u2663\uFE0F',
  '\u{1F680}','\u{1F6F8}','\u{1F6F0}\uFE0F','\u{1F30C}','\u{1FA90}','\u{1F3D4}\uFE0F','\u{1F5FB}','\u{1F30F}','\u{1F310}','\u{1F5FA}\uFE0F','\u{1F9ED}','\u{1F3DD}\uFE0F','\u{1F3DC}\uFE0F','\u{1F303}','\u{1F306}',
  '\u{1F480}','\u{1F47E}','\u{1F383}','\u{1F47B}','\u26B0\uFE0F','\u{1F56F}\uFE0F','\u{1FAA6}','\u262F\uFE0F','\u26A0\uFE0F','\u{1F300}',
  '\u{1FAC0}','\u{1F9E0}','\u{1F9B7}','\u{1F9B4}','\u{1F441}\uFE0F',
  '\u{1F391}','\u{1F3FA}','\u{1F5FC}','\u{1F3EF}','\u{1F4A7}','\u26C4','\u{1F451}','\u{1F48D}','\u{1F514}','\u{1F390}','\u{1F38F}','\u{1FA69}',
  '\u{1F9F6}','\u{1F9F5}','\u{1F3DB}\uFE0F','\u{1F3F0}','\u{1F302}',
  '\u{1F9E9}','\u{1FA94}','\u{1F3EE}','\u{1F48A}','\u{1FA7A}','\u{1FA7B}',
  '\u{1F7E5}','\u{1F7E7}','\u{1F7E8}','\u{1F7E9}','\u{1F7E6}','\u{1F7EA}','\u{1F7EB}',
  '\u{1F43E}','\u{1F9B6}','\u{1F463}','\u{1F33F}','\u{1F343}','\u{1F33E}','\u{1F38B}',
  '\u{1FAB8}','\u{1F9A0}','\u{1FAB2}','\u{1FAB3}','\u{1FAB0}','\u{1FAB1}',
  '\u{1FAC6}','\u{1FAF3}','\u{1FAF4}','\u{1FAF5}','\u{1F90C}','\u{1F90F}',
  '\u{1FAC2}','\u{1F9FF}','\u{1F52F}','\u2721\uFE0F','\u262A\uFE0F','\u26CE','\u2648','\u2649','\u264A','\u264B','\u264C','\u264D','\u264E','\u264F','\u2650','\u2651','\u2652','\u2653',
];

// -- DECO SETS --
const DECO_SETS=[
  ['\u272E','\u2620','\u2602','\u2601','\u2600','\u263C','\u263D','\u263E','\u2623','\u2740','\u0457','\u2604','\u272F','\u2663','\u2667','\u25D4','\u25D5','\u266C','\u273D','\u266B','\u266A','\u00B0','\u2743','\u2749','\u2723','\u2042','\u2726','*','.'],
  ['\u2591','\u2592','\u2593','\u2502','\u2524','\u2554','\u2557','\u255A','\u255D','\u2500','\u2550','\u2560','\u2563','\u2566','\u2569','\u256C','\u2590','\u258C','\u2580','\u2584','\u25AA','\u25AB'],
  ['\u2234','\u2235','\u221E','\u2261','\u2207','\u22EE','\u2211','\u220F','\u2202','\u222B','\u221A','\u2206','\u2248','\u2203','\u2200','\u2208','\u2295','\u2297','\u2299','\u222F','\u225C'],
  ['\u16A0','\u16A2','\u16A6','\u16A8','\u16B1','\u16B2','\u16B7','\u16B9','\u16BA','\u16BE','\u16C1','\u16C3','\u16C7','\u16C8','\u16C9','\u16CA','\u16CF','\u16D2','\u16D6','\u16D7','\u16DA','\u16DC'],
  ['\u283F','\u282F','\u2837','\u283E','\u2838','\u283C','\u283B','\u283D','\u2831','\u2829','\u2819','\u280B','\u2803','\u2805','\u2807','\u280F','\u281F','\u2817','\u281B','\u2813','\u281A','\u2822'],
];

const SPACE_CHARS=['\u00B7','\u2219','\u2022','\u25E6','\u2218','\u2058','\u2059','\u205A','\u2234','\u2235','\uFF61',':','\u00B0'];
const FRAME_EMOJIS=['\u2B1B','\u{1F532}','\u{1F533}','\u25FC\uFE0F','\u25AA\uFE0F','\u2B1C','\u25FB\uFE0F','\u25AB\uFE0F'];
const ALL_DECO=new Set([...DECO_SETS.flat(),...SPACE_CHARS,...FRAME_EMOJIS]);

const RU_CHARS=Array.from('\u0410\u0411\u0412\u0413\u0414\u0415\u0401\u0416\u0417\u0418\u0419\u041A\u041B\u041C\u041D\u041E\u041F\u0420\u0421\u0422\u0423\u0424\u0425\u0426\u0427\u0428\u0429\u042A\u042B\u042C\u042D\u042E\u042F');
const EN_CHARS=Array.from('ABCDEFGHIJKLMNOPQRSTUVWXYZ');
const DIGITS=Array.from('0123456789');

const RU_BIGRAMS=[
  '\u0421\u0422','\u041D\u0410','\u0415\u041D','\u0422\u041E','\u041D\u041E','\u0420\u0410','\u041D\u0418','\u041D\u0415','\u0412\u041E','\u041E\u0422','\u041E\u0412','\u0415\u0422','\u0420\u041E','\u041E\u0421',
  '\u041A\u041E','\u041F\u041E','\u041F\u0420','\u0410\u041B','\u041B\u0410','\u041E\u041D','\u0410\u041D','\u0412\u0410','\u041B\u0418','\u0420\u0415','\u0418\u0422','\u041B\u0415','\u0421\u0410','\u0417\u0410','\u041C\u0410','\u0410\u0422',
  '\u041E\u041C','\u0415\u0421','\u0412\u0415','\u0422\u0415','\u0418\u0415','\u041A\u0410','\u0415\u0420','\u0418\u041D','\u0422\u0410','\u0427\u0422',
  '\u0414\u041E','\u0415\u041B','\u0415\u041C','\u0415\u0414','\u0415\u041A','\u0417\u041D','\u0418\u0412','\u0418\u0413','\u0418\u0414','\u0418\u0419','\u0418\u041B','\u0418\u041C','\u0418\u041E','\u0418\u0421','\u0418\u042F',
  '\u041B\u041E','\u041C\u041E','\u041C\u0423','\u041D\u0415','\u041D\u042C','\u041D\u042E','\u041D\u042F','\u041E\u0414','\u041E\u0419','\u041E\u041A','\u041E\u041B','\u041E\u041D','\u041E\u041F','\u041E\u0421','\u041E\u0425',
  '\u0420\u0418','\u0420\u0423','\u0421\u0415','\u0421\u0418','\u0421\u041A','\u0421\u041E','\u0422\u0412','\u0422\u0418','\u0422\u042C','\u0423\u0429'
];

const ART_PAD=['\u{1F338}','\u{1F33A}','\u{1F33C}','\u{1F4AE}','\u{1F339}','\u{1FAB7}','\u{1F33B}','\u{1F308}','\u2B50','\u{1F31F}','\u{1F4AB}','\u2728','\u{1F48E}','\u{1F319}','\u{1F30A}','\u{1F340}','\u{1F386}'];

const PIXEL_ARTS={
  house:[[0,0,1,1,1,0,0],[0,1,1,1,1,1,0],[1,1,1,1,1,1,1],[1,1,0,1,1,0,1],[1,1,0,1,1,0,1],[1,1,1,0,0,1,1],[1,1,1,1,1,1,1]],
  sun:  [[0,1,0,1,0,1,0],[1,0,1,1,1,0,1],[0,1,1,1,1,1,0],[1,1,1,1,1,1,1],[0,1,1,1,1,1,0],[1,0,1,1,1,0,1],[0,1,0,1,0,1,0]],
  cat:  [[1,1,0,0,0,1,1],[1,1,1,1,1,1,1],[1,0,1,1,1,0,1],[1,1,1,1,1,1,1],[0,1,1,1,1,1,0],[1,0,0,0,0,0,1],[0,0,0,0,0,0,0]],
  heart:[[0,1,1,0,1,1,0],[1,1,1,1,1,1,1],[1,1,1,1,1,1,1],[0,1,1,1,1,1,0],[0,0,1,1,1,0,0],[0,0,0,1,0,0,0],[0,0,0,0,0,0,0]],
  moon: [[0,0,1,1,1,0,0],[0,1,1,0,0,0,0],[1,1,0,0,0,0,0],[1,1,0,0,0,0,0],[1,1,0,0,0,0,0],[0,1,1,0,0,0,0],[0,0,1,1,1,0,0]],
  star: [[0,0,0,1,0,0,0],[0,1,0,1,0,1,0],[0,0,1,1,1,0,0],[1,1,1,1,1,1,1],[0,0,1,1,1,0,0],[0,1,0,0,0,1,0],[1,0,0,0,0,0,1]],
  skull:[[0,1,1,1,1,1,0],[1,1,1,1,1,1,1],[1,0,1,1,1,0,1],[1,1,1,1,1,1,1],[0,1,1,1,1,1,0],[0,1,0,1,0,1,0],[0,0,1,1,1,0,0]],
};
const ART_KEYS=Object.keys(PIXEL_ARTS);

// -- HELPERS --
function shuffled(arr){const a=[...arr];for(let i=a.length-1;i>0;i--){const j=~~(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}

function parseEmojis(raw){
  try{const seg=new Intl.Segmenter('en',{granularity:'grapheme'});return Array.from(seg.segment(raw)).map(s=>s.segment);}
  catch(e){return Array.from(raw.matchAll(/\p{Emoji_Presentation}|\p{Emoji}\uFE0F|./gu)).map(m=>m[0]);}
}

// -- TOKEN CODEC --
function encodeToken(obj){
  const pidx={};EMOJI_POOL.forEach((e,i)=>pidx[e]=i);
  const mapInts=m=>Object.fromEntries(Object.entries(m).map(([k,vs])=>[k,vs.map(e=>pidx[e]??e)]));
  const c={
    i:obj.id,n:obj.name,v:3,
    m:obj.mode?obj.mode[0]:'r',
    t:obj.type?obj.type[0]:'m',
    l:obj.letters?mapInts(obj.letters):{},
    b:obj.bigrams?mapInts(obj.bigrams):{},
    s:obj.spaceEmoji!=null?(pidx[obj.spaceEmoji]??obj.spaceEmoji):null,
    p:obj.spaceSep||'\u00B7',
    d:obj.decoStyle??0,
    x:(obj.nullEmojis||[]).map(e=>pidx[e]??e),
    c:obj.created?obj.created.slice(0,10):'',
    ttl:obj.ttl??null,
    rv:obj.rev_mapping?mapInts2(obj.rev_mapping,pidx):undefined,
    si:obj.source_id,
  };
  Object.keys(c).forEach(k=>c[k]===undefined&&delete c[k]);
  return btoa(unescape(encodeURIComponent(JSON.stringify(c))));
}

function mapInts2(m,pidx){
  if(!pidx){pidx={};EMOJI_POOL.forEach((e,i)=>pidx[e]=i);}
  return Object.fromEntries(Object.entries(m).map(([e,ch])=>[pidx[e]??e,ch]));
}

function decodeToken(b64){
  try{
    const json=decodeURIComponent(escape(atob(b64)));
    const c=JSON.parse(json);
    if(c.letters&&typeof Object.values(c.letters)[0]?.[0]==='string'){c._b64=b64;return c;}
    const fromIdx=x=>typeof x==='number'?EMOJI_POOL[x]:x;
    const expandMap=m=>Object.fromEntries(Object.entries(m).map(([k,vs])=>[k,(Array.isArray(vs)?vs:[vs]).map(fromIdx)]));
    const modeMap={r:'ru',e:'en',b:'both'};
    const obj={
      id:c.i,name:c.n,v:3,
      mode:modeMap[c.m]||'ru',
      type:c.t==='r'?'reader':'master',
      letters:c.l?expandMap(c.l):{},
      bigrams:c.b?expandMap(c.b):{},
      spaceEmoji:c.s!=null?fromIdx(c.s):null,
      spaceSep:c.p||'\u00B7',
      decoStyle:c.d||0,
      nullEmojis:(c.x||[]).map(fromIdx),
      created:c.c?c.c+'T00:00:00Z':new Date().toISOString(),
      ttl:c.ttl??null,
    };
    if(c.rv){
      obj.rev_mapping=Object.fromEntries(Object.entries(c.rv).map(([k,v])=>[fromIdx(Number.isFinite(+k)?+k:k),v]));
      obj.source_id=c.si;
    }
    obj._b64=b64;
    return obj;
  }catch(e){return null;}
}

// -- GENERATE TOKEN --
function generateToken(name, mode){
  let chars=[];
  if(mode==='ru'||mode==='both')chars=[...chars,...RU_CHARS];
  if(mode==='en'||mode==='both')chars=[...chars,...EN_CHARS];
  chars=[...chars,...DIGITS];

  const pool=shuffled([...EMOJI_POOL]);
  const used=new Set([...FRAME_EMOJIS]);

  let spaceEmoji=null;
  for(const e of pool){if(!used.has(e)){used.add(e);spaceEmoji=e;break;}}

  function assign(n){
    const res=[];
    for(const e of pool){if(res.length>=n)break;if(!used.has(e)){used.add(e);res.push(e);}}
    return res;
  }

  const letters={};
  const RU_HI=new Set(Array.from('\u0410\u0415\u041E\u0418\u0423\u0422\u041D\u0421\u0420\u041B'));
  for(const ch of chars){
    const n=RU_HI.has(ch)?3:RU_CHARS.includes(ch)?2:EN_CHARS.includes(ch)?2:1;
    const hs=assign(n);
    if(hs.length)letters[ch]=hs;
  }

  const bigrams={};
  if(mode==='ru'||mode==='both'){
    for(const bg of RU_BIGRAMS.slice(0,40)){
      const hs=assign(2);
      if(hs.length)bigrams[bg]=hs;
    }
  }

  const nullEmojis=pool.filter(e=>!used.has(e)).slice(0,12);
  const decoStyle=~~(Math.random()*DECO_SETS.length);
  const spaceSep=SPACE_CHARS[~~(Math.random()*SPACE_CHARS.length)];

  const id='lang_'+Date.now();
  const obj={id,name,letters,bigrams,spaceEmoji,spaceSep,nullEmojis,decoStyle,
    created:new Date().toISOString(),mode,type:'master',ttl:null,v:3};
  obj._b64=encodeToken(obj);
  return obj;
}

// -- READER TOKEN --
function generateReaderToken(masterLang){
  if(!masterLang||masterLang.type==='reader')return null;
  const rev={};
  for(const[ch,hs]of Object.entries(masterLang.letters||{}))for(const e of hs)rev[e]=ch;
  for(const[bg,hs]of Object.entries(masterLang.bigrams||{}))for(const e of hs)rev[e]=bg;
  if(masterLang.spaceEmoji)rev[masterLang.spaceEmoji]=' ';
  const rObj={id:'reader_'+Date.now(),name:masterLang.name+'_READ',type:'reader',
    rev_mapping:rev,nullEmojis:masterLang.nullEmojis,decoStyle:masterLang.decoStyle,
    spaceSep:masterLang.spaceSep,source_id:masterLang.id,created:new Date().toISOString(),
    ttl:masterLang.ttl,v:3};
  rObj._b64=encodeToken(rObj);
  return rObj;
}

// -- ENCODE --
function encodeStr(text,lang){
  if(!lang||lang.type==='reader')return[];
  const L=lang.letters||{};const B=lang.bigrams||{};
  const T=text.toUpperCase();
  const result=[];let i=0;
  while(i<T.length){
    const c1=T[i],c2=T.slice(i,i+2);
    if(c1===' '){
      if(lang.spaceEmoji)result.push(lang.spaceEmoji);
      else if(lang.nullEmojis?.[0])result.push(lang.nullEmojis[0]);
      i++;
    } else if(B[c2]&&i+1<T.length&&T[i+1]!==' '){
      const hs=B[c2];result.push(hs[~~(Math.random()*hs.length)]);i+=2;
    } else if(L[c1]){
      const hs=L[c1];result.push(hs[~~(Math.random()*hs.length)]);i++;
    } else i++;
  }
  return result;
}

function addNulls(arr,nulls,density){
  if(!nulls?.length||density<=0)return arr;
  const r=[];for(const e of arr){r.push(e);if(Math.random()<density)r.push(nulls[~~(Math.random()*nulls.length)]);}
  return r;
}

function addAnchor(arr,shape,nulls){
  if(!nulls||nulls.length<5)return arr;
  const shapes=['grid','triangle','diamond','cross','frame'];
  const si=shapes.indexOf(shape);const anchor=nulls[si>=0?si:0];
  return[anchor,...arr,anchor];
}

function extractAnchor(emojis,nulls){
  if(!emojis.length||!nulls?.length)return null;
  const shapes=['grid','triangle','diamond','cross','frame'];
  if(emojis.length>=2&&emojis[0]===emojis[emojis.length-1]){
    const si=nulls.indexOf(emojis[0]);
    if(si>=0&&si<shapes.length)return{shape:shapes[si],strip:true};
  }
  return null;
}

function artModeWrap(encoded){
  const target=Math.pow(Math.ceil(Math.sqrt(encoded.length*3)),2);
  const r=[...encoded];
  while(r.length<target){r.splice(~~(Math.random()*r.length),0,ART_PAD[~~(Math.random()*ART_PAD.length)]);}
  return r;
}

// -- DECODE --
function buildRevMap(lang){
  const rev={};
  if(lang.type==='reader'){Object.assign(rev,lang.rev_mapping||{});return rev;}
  for(const[ch,hs]of Object.entries(lang.letters||{}))for(const e of hs)rev[e]=ch;
  for(const[bg,hs]of Object.entries(lang.bigrams||{}))for(const e of hs)rev[e]=bg;
  if(lang.spaceEmoji)rev[lang.spaceEmoji]=' ';
  return rev;
}

function decode(raw,lang){
  const rev=buildRevMap(lang);
  const allClusters=parseEmojis(raw);
  const meaningful=allClusters.filter(c=>{const t=c.trim();return t&&!ALL_DECO.has(t)&&!/^[\s\n\r\u3000\u2800]+$/.test(c);});
  let decodeArr=meaningful,anchorShape=null;
  const anch=extractAnchor(meaningful,lang.nullEmojis||[]);
  if(anch){anchorShape=anch.shape;if(anch.strip)decodeArr=meaningful.slice(1,-1);}
  let decoded='',found=0,miss=0;
  for(const e of decodeArr){
    if(rev[e]!==undefined){decoded+=rev[e];found++;}
    else if(!(lang.nullEmojis||[]).includes(e)&&!ART_PAD.includes(e))miss++;
  }
  return{decoded,found,miss,anchorShape};
}

// -- SHAPES --
let _lastArtKey=ART_KEYS[0];

function buildArtRows(emojis,artKey){
  const tmpl=PIXEL_ARTS[artKey]||PIXEL_ARTS.house;
  const PAD=FRAME_EMOJIS[0];
  const rows=[];let ei=0;
  for(const tRow of tmpl){rows.push(tRow.map(cell=>cell?emojis[ei++%emojis.length]:PAD));}
  return rows;
}

function buildRows(emojis,shape){
  const e=[...emojis],rows=[];if(!e.length)return rows;
  if(shape==='rnd'){_lastArtKey=ART_KEYS[~~(Math.random()*ART_KEYS.length)];return buildArtRows(emojis,_lastArtKey);}
  switch(shape){
    case 'grid':{const c=Math.max(3,Math.ceil(Math.sqrt(e.length)));for(let i=0;i<e.length;i+=c)rows.push(e.slice(i,i+c));break;}
    case 'triangle':{let i=0,r=1;while(i<e.length){rows.push(e.slice(i,i+r));i+=r;r++;}break;}
    case 'diamond':{const mid=Math.max(3,Math.ceil(Math.sqrt(e.length)));let i=0,r=1,dir=1;while(i<e.length){rows.push(e.slice(i,i+r));i+=r;if(r>=mid)dir=-1;r=Math.max(1,r+dir);}break;}
    case 'cross':{const w=Math.max(5,Math.ceil(Math.sqrt(e.length*1.6)));const stub=Math.max(1,~~(w/3));let i=0;for(let ri=0;ri<stub&&i<e.length;ri++){rows.push(e.slice(i,i+stub));i+=stub;}const midRows=Math.max(1,Math.ceil((e.length-stub*stub*2)/w));for(let ri=0;ri<midRows&&i<e.length;ri++){rows.push(e.slice(i,i+w));i+=w;}while(i<e.length){rows.push(e.slice(i,i+stub));i+=stub;}break;}
    case 'frame':{const w=Math.max(4,Math.ceil(Math.sqrt(e.length*1.2)));let i=0;rows.push(e.slice(0,Math.min(w,e.length)));i+=w;while(i+w<=e.length-w){rows.push(e.slice(i,i+2));i+=2;}if(i<e.length)rows.push(e.slice(i));break;}
    default:{const c=Math.ceil(Math.sqrt(e.length));for(let i=0;i<e.length;i+=c)rows.push(e.slice(i,i+c));}
  }
  return rows;
}

// -- COPY MODES --
function rowsToFlat(rows){return rows.flat().join('');}

function rowsToShaped(rows,decoStyle){
  const PAD=FRAME_EMOJIS[(decoStyle||0)%FRAME_EMOJIS.length];
  const maxW=Math.max(...rows.map(r=>r.length));
  return rows.map(row=>{
    const padL=Math.floor((maxW-row.length)/2);
    const padR=maxW-row.length-padL;
    return[...Array(padL).fill(PAD),...row,...Array(padR).fill(PAD)].join('');
  }).join('\n');
}

function rowsToArtistic(rows,decoStyle,spaceSep){
  const PAD=FRAME_EMOJIS[(decoStyle||0)%FRAME_EMOJIS.length];
  const maxW=Math.max(...rows.map(r=>r.length));
  const ds=DECO_SETS[(decoStyle||0)%DECO_SETS.length];
  const rowVisualW=maxW*2+(maxW-1);
  const body=rows.map((row,ri)=>{
    const padL=Math.floor((maxW-row.length)/2);
    const padR=maxW-row.length-padL;
    const full=[...Array(padL).fill(PAD),...row,...Array(padR).fill(PAD)];
    const inner=full.map((e,i)=>i<full.length-1?e+ds[(ri*5+i*3+7)%ds.length]:e).join('');
    return ds[(ri*3)%ds.length]+inner+ds[(ri*3+4)%ds.length];
  }).join('\n');
  const fullW=rowVisualW+2;
  const topLine=Array.from({length:fullW},(_,i)=>ds[(i+3)%ds.length]).join('');
  const botLine=Array.from({length:fullW},(_,i)=>ds[(fullW-i+7)%ds.length]).join('');
  return topLine+'\n'+body+'\n'+botLine;
}

// -- PUBLIC API --
return {
  EMOJI_POOL, DECO_SETS, SPACE_CHARS, FRAME_EMOJIS, ALL_DECO,
  RU_CHARS, EN_CHARS, DIGITS, RU_BIGRAMS, ART_PAD,
  PIXEL_ARTS, ART_KEYS,
  shuffled, parseEmojis,
  encodeToken, decodeToken,
  generateToken, generateReaderToken,
  encodeStr, addNulls, addAnchor, extractAnchor, artModeWrap,
  buildRevMap, decode,
  buildArtRows, buildRows,
  rowsToFlat, rowsToShaped, rowsToArtistic,
  get lastArtKey(){ return _lastArtKey; },
  set lastArtKey(v){ _lastArtKey = v; },
};

})();
