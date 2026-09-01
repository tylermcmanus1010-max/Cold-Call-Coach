// Area code to state, for the markets this tool searches.
//
// OpenStreetMap listings frequently carry no addr:state, and a national list
// without a state is useless — Tyler needs to know whether he is about to ring
// somewhere three time zones away. The area code is on the number he is about
// to dial, so it is the one piece of evidence always present.
//
// This is an inference, not a fact off the listing: numbers move, and a mobile
// keeps its code across a move. Rows filled in this way are marked as derived
// so nothing downstream presents them as the listing's own data.

const MAP = {
  AZ: [480, 520, 602, 623, 928],
  CA: [209, 213, 279, 310, 323, 341, 350, 408, 415, 424, 442, 510, 530, 559, 562, 619, 626, 628,
       650, 657, 661, 669, 707, 714, 747, 760, 805, 818, 820, 831, 840, 858, 909, 916, 925, 949, 951],
  CO: [303, 719, 720, 970, 983],
  DE: [302],
  FL: [239, 305, 321, 352, 386, 407, 448, 561, 656, 689, 727, 754, 772, 786, 813, 850, 863, 904, 941, 954],
  IN: [219, 260, 317, 463, 574, 765, 812, 930],
  NC: [252, 336, 704, 743, 828, 910, 919, 980, 984],
  NE: [308, 402, 531],
  NJ: [201, 551, 609, 640, 732, 848, 856, 862, 908, 973],
  OH: [216, 220, 234, 326, 330, 380, 419, 440, 513, 567, 614, 740, 937],
  OK: [405, 539, 572, 580, 918],
  TN: [423, 615, 629, 731, 865, 901, 931],
  WA: [206, 253, 360, 425, 509, 564],
  WI: [262, 274, 414, 534, 608, 715, 920],
};

const BY_CODE = new Map();
for (const [state, codes] of Object.entries(MAP)) {
  for (const c of codes) BY_CODE.set(String(c), state);
}

// Toll-free codes belong to no state and must never be resolved to one.
const TOLL_FREE = new Set(['800', '833', '844', '855', '866', '877', '888']);

module.exports = function stateFromPhone(phone) {
  const d = String(phone || '').replace(/[^0-9]/g, '').replace(/^1(?=\d{10}$)/, '');
  if (d.length !== 10) return '';
  const code = d.slice(0, 3);
  if (TOLL_FREE.has(code)) return '';
  return BY_CODE.get(code) || '';
};
