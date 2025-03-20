import { languages, Range } from 'monaco-editor';
import { pinyin } from 'pinyin-pro';

const cards = ['小野', '绿弓', '咕咕'];

const cardsInPinyin = cards.map((card) =>
  pinyin(card, { toneType: 'none', type: 'string' })
);

export const getEditorSuggestions = (
  type: languages.CompletionItemKind,
  range: Range,
): languages.CompletionItem[] => {
  const chineseList = cards.map((card) => ({
    label: card,
    insertText: card,
    kind: type,
    range: range,
  }));
  const pinyinList = cardsInPinyin.map((card, index) => ({
    label: `${card}(${cards[index]})`,
    insertText: cards[index],
    kind: type,
    range: range,
  }));
  return [...chineseList, ...pinyinList];
};