import { languages, Range } from 'monaco-editor';
import { pinyin } from 'pinyin-pro';

const cards = ['小野', '绿弓', '咕咕'];
const actions = ['上', '下']

const allChinese = [...cards,...actions]

const allPinyin = allChinese.map((card) =>
  pinyin(card, { toneType: 'none', type: 'string' })
);

export const getEditorSuggestions = (
  type: languages.CompletionItemKind,
  range: Range,
): languages.CompletionItem[] => {
  const chineseList = allChinese.map((card) => ({
    label: card,
    insertText: card,
    kind: type,
    range: range,
  }));
  const pinyinList = allPinyin.map((card, index) => ({
    label: `${card}(${allChinese[index]})`,
    insertText: allChinese[index],
    kind: type,
    range: range,
  }));
  return [...chineseList, ...pinyinList];
};