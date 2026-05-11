/**
 * イースターエッグ機能
 * 医薬品推奨アプリケーションの面白機能
 */

// 医療用語リスト（security_validator.pyのMEDICAL_TERMSから取得）
// 1語でも検出された場合は通常処理にフォールバック
const MEDICAL_TERMS = new Set([
    // 症状関連
    '頭痛', '頭が痛い', '頭がズキズキ', '偏頭痛', '緊張性頭痛',
    '発熱', '熱がある', '高熱', '微熱', '体温上昇',
    '咳', 'せき', '咳が出る', '咳が止まらない', '痰が絡む',
    '鼻水', '鼻づまり', '鼻が詰まる', 'くしゃみ', '鼻炎',
    'のどの痛み', '喉が痛い', '咽頭痛', '声がかすれる',
    '腹痛', 'お腹が痛い', '胃痛', '胃が痛い', '下腹部痛',
    '下痢', '軟便', '水様便', '便がゆるい', '便が緩い',
    '便秘', '便が出ない', '便通がない', '便が硬い',
    '吐き気', 'むかつき', '気持ち悪い', '嘔吐感', '吐きそう',
    '胸やけ', '胸焼け', '胃もたれ', '胃の重い感じ', '消化不良',
    'めまい', '眩暈', 'ふらつき', '立ちくらみ', '平衡感覚の異常',
    '疲労感', '疲れ', 'だるい', '倦怠感', '体が重い',
    '不眠', '眠れない', '睡眠不足', '寝つきが悪い', '浅い眠り',
    'かゆみ', '痒み', 'かゆい', '皮膚のかゆみ', '全身のかゆみ',
    '発疹', 'ブツブツ', '赤い斑点', '皮膚の異常', '湿疹',
    '目の疲れ', '眼精疲労', '目が疲れる', '目の重い感じ',
    '目のかゆみ', '目がかゆい', '目の痒み', '結膜炎',
    '関節痛', '関節が痛い', '筋肉痛', '筋肉が痛い', '肩こり',
    '腰痛', '腰が痛い', '背中の痛み', '首の痛み',
    'イライラ', 'イライラする', '神経質', '不安', 'ストレス',
    '動悸', '心臓がドキドキ', '息切れ', '呼吸困難',
    '冷え性', '手足が冷える', '寒気', '悪寒', '震え',
    // 医薬品関連
    '風邪薬', '解熱鎮痛薬', '鼻炎用薬', '胃腸薬', '外用薬',
    '目薬', '睡眠薬', '咳止め', '痰切り', '整腸剤',
    'アセトアミノフェン', 'イブプロフェン', 'ロキソプロフェン',
    'アスピリン', 'ジクロフェナク', 'ケトプロフェン',
    // 身体部位
    '頭', '頭部', '額', 'こめかみ', '後頭部',
    '目', '眼球', 'まぶた', '涙腺', '角膜',
    '鼻', '鼻腔', '副鼻腔', '鼻粘膜', '鼻中隔',
    '口', '口腔', '舌', '歯', '歯茎', 'のど', '喉',
    '胸', '胸部', '心臓', '肺', '気管', '気管支',
    'お腹', '腹部', '胃', '腸', '十二指腸', '大腸', '小腸',
    '腰', '腰部', '背中', '脊椎', '腰椎', '胸椎',
    '手足', '腕', '脚', '足', '手', '指', '関節',
    '皮膚', '表皮', '真皮', '毛細血管', '汗腺',
    // 症状の程度・期間
    '軽い', '軽度', '少し', 'ちょっと', '弱い',
    '中程度', '普通', 'まあまあ', 'そこそこ',
    '重い', '重度', 'ひどい', '激しい', '強い',
    '急性', '慢性', '一時的', '継続的', '断続的',
    '突然', '急に', '徐々に', 'だんだん', '次第に',
    '昨日から', '今日から', '今朝から', '昨夜から',
    '一週間', '数日', '数時間', '数分', '数秒',
    'ずっと', '常に', '時々', 'たまに', 'まれに'
]);

// 感謝・ポジティブメッセージのトリガーリスト
const THANKS_TRIGGERS = new Set([
    // 日本語
    'ありがとう', 'ありがとうございます', '助かった', '助かりました',
    '完治した', '治った', '良くなった', '感謝', '素晴らしい', '最高', '完璧',
    // 英語
    'thank you', 'thanks', 'helped', 'cured', 'healed', 'better',
    'grateful', 'great', 'perfect', 'excellent'
]);

// 画面変形系のトリガー（完全一致チェック用）
const TRANSFORM_TRIGGERS = {
    rotate: new Set([
        // 基本形
        '回転', 'かいてん', 'rotate', '回る', 'まわる', 'spin', 'twirl',
        // 命令形
        '回転しろ', '回転して', '回転させて', '回転してください', '回転してくれ', '回転してよ',
        '回れ', 'まわれ', '回って', '回ってください', '回ってくれ',
        'spin', 'rotate it', 'rotate please', 'turn', 'turn around',
        // 演繹形
        '回転する', '回転させる', '回転します', '回転させます',
        '回るように', 'まわるように',
        // 魔法使い・呪文系
        '回転の魔法', '回転呪文', '回転スペル', '回転の呪文',
        'rotate magic', 'rotate spell', 'rotation spell',
        // その他
        '回転させろ', '回転しなさい', '回転しろよ'
    ]),
    skew: new Set([
        // 基本形
        '傾く', 'かたむく', 'askew', '傾斜', 'けいしゃ', 'tilt', 'lean',
        // 命令形
        '傾け', 'かたむけ', '傾けて', 'かたむけて', '傾けてください', '傾けてくれ',
        '傾けろ', 'かたむけろ', '傾けなさい',
        'tilt', 'tilt it', 'tilt please', 'lean', 'lean it',
        // 演繹形
        '傾ける', 'かたむける', '傾けます', 'かたむけます',
        '傾くように', 'かたむくように',
        // 魔法使い・呪文系
        '傾きの魔法', '傾き呪文', '傾斜の魔法', '傾斜呪文',
        'tilt magic', 'tilt spell', 'skew spell',
        // その他
        '傾斜させて', '傾斜してください'
    ]),
    shake: new Set([
        // 基本形
        '揺れる', 'ゆれる', 'shake', '震える', 'ふるえる', 'tremble', 'vibrate',
        // 命令形
        '揺らせ', 'ゆらせ', '揺らして', 'ゆらして', '揺らしてください', '揺らしてくれ',
        '震えろ', 'ふるえろ', '震えて', 'ふるえて', '震えてください',
        'shake', 'shake it', 'shake please', 'tremble', 'vibrate',
        // 演繹形
        '揺らす', 'ゆらす', '揺らします', 'ゆらします',
        '震わせる', 'ふるわせる', '震わせます',
        '揺れるように', 'ゆれるように',
        // 魔法使い・呪文系
        '揺れの魔法', '揺れ呪文', '震えの魔法', '震え呪文',
        'shake magic', 'shake spell', 'tremble spell',
        // その他
        '揺らせろ', 'ゆらせろ', '揺らしなさい'
    ]),
    zoom: new Set([
        // 基本形
        '拡大', 'かくだい', 'zoom', 'ズーム', '拡大縮小', 'scale', 'magnify',
        // 命令形
        '拡大しろ', 'かくだいしろ', '拡大して', 'かくだいして', '拡大してください', '拡大してくれ',
        '拡大させて', 'かくだいさせて', '拡大させてください',
        'zoom', 'zoom in', 'zoom out', 'zoom please', 'scale', 'scale it',
        // 演繹形
        '拡大する', 'かくだいする', '拡大します', 'かくだいします',
        '拡大させる', 'かくだいさせる', '拡大させます',
        '拡大するように', 'かくだいするように',
        // 魔法使い・呪文系
        '拡大の魔法', '拡大呪文', 'ズームの魔法', 'ズーム呪文',
        'zoom magic', 'zoom spell', 'scale spell',
        // その他
        '拡大しなさい', 'かくだいしなさい', '拡大縮小して'
    ]),
    flip: new Set([
        // 基本形
        '反転', 'はんてん', 'flip', 'ひっくり返す', '裏返し', 'reverse', 'mirror',
        // 命令形
        '反転しろ', 'はんてんしろ', '反転して', 'はんてんして', '反転してください', '反転してくれ',
        'ひっくり返せ', 'ひっくり返して', 'ひっくり返してください', 'ひっくり返してくれ',
        'flip', 'flip it', 'flip please', 'reverse', 'reverse it', 'mirror',
        // 演繹形
        '反転する', 'はんてんする', '反転します', 'はんてんします',
        'ひっくり返す', 'ひっくり返します',
        '反転するように', 'はんてんするように',
        // 魔法使い・呪文系
        '反転の魔法', '反転呪文', '裏返しの魔法', '裏返し呪文',
        'flip magic', 'flip spell', 'reverse spell',
        // その他
        '反転しなさい', 'はんてんしなさい', '裏返して'
    ]),
    bounce: new Set([
        // 基本形
        'バウンス', '跳ねる', 'はねる', 'bounce', '弾む', 'はずむ', 'jump',
        // 命令形
        '跳ねろ', 'はねろ', '跳ねて', 'はねて', '跳ねてください', '跳ねてくれ',
        '弾め', 'はずめ', '弾んで', 'はずんで', '弾んでください', '弾んでくれ',
        'bounce', 'bounce it', 'bounce please', 'jump', 'jump it',
        // 演繹形
        '跳ねる', 'はねる', '跳ねます', 'はねます',
        '弾む', 'はずむ', '弾みます', 'はずみます',
        '跳ねるように', 'はねるように',
        // 魔法使い・呪文系
        '跳ねの魔法', '跳ね呪文', 'バウンスの魔法', 'バウンス呪文',
        'bounce magic', 'bounce spell', 'jump spell',
        // その他
        '跳ねしなさい', 'はねしなさい', 'バウンスして'
    ]),
    pulse: new Set([
        // 基本形
        '脈動', 'みゃくどう', 'pulse', '鼓動', 'こどう', 'beat', 'throb',
        // 命令形
        '脈動しろ', 'みゃくどうしろ', '脈動して', 'みゃくどうして', '脈動してください', '脈動してくれ',
        '鼓動しろ', 'こどうしろ', '鼓動して', 'こどうして', '鼓動してください',
        'pulse', 'pulse it', 'pulse please', 'beat', 'beat it', 'throb',
        // 演繹形
        '脈動する', 'みゃくどうする', '脈動します', 'みゃくどうします',
        '鼓動する', 'こどうする', '鼓動します', 'こどうします',
        '脈動するように', 'みゃくどうするように',
        // 魔法使い・呪文系
        '脈動の魔法', '脈動呪文', '鼓動の魔法', '鼓動呪文',
        'pulse magic', 'pulse spell', 'beat spell',
        // その他
        '脈動しなさい', 'みゃくどうしなさい', '鼓動しなさい'
    ]),
    glow: new Set([
        // 基本形
        '光る', 'ひかる', 'glow', '輝く', 'かがやく', 'shine', 'bright',
        // 命令形
        '光れ', 'ひかれ', '光って', 'ひかって', '光ってください', '光ってくれ',
        '輝け', 'かがやけ', '輝いて', 'かがやいて', '輝いてください', '輝いてくれ',
        'glow', 'glow it', 'glow please', 'shine', 'shine it', 'bright',
        // 演繹形
        '光る', 'ひかる', '光ります', 'ひかります',
        '輝く', 'かがやく', '輝きます', 'かがやきます',
        '光るように', 'ひかるように',
        // 魔法使い・呪文系
        '光の魔法', '光呪文', '輝きの魔法', '輝き呪文', '光る魔法', '輝く魔法',
        'glow magic', 'glow spell', 'shine spell', 'bright spell',
        // その他
        '光りなさい', 'ひかりなさい', '輝きなさい', 'かがやきなさい'
    ])
};

// ゲーム系のトリガー
const GAME_TRIGGERS = {
    snake: new Set(['スネーク', 'スネークゲーム', 'snake', 'snake game']),
    emoji: null // 絵文字のみの場合は正規表現で判定
};

// アニメーション系のトリガー
const ANIMATION_TRIGGERS = {
    fireworks: new Set(['花火', 'はなび', 'fireworks']),
    snow: new Set(['雪', 'ゆき', 'snow']),
    rain: new Set(['雨', 'あめ', 'rain'])
};

// 特別イベント系のトリガー
const SPECIAL_EVENT_TRIGGERS = {
    newyear: new Set([
        // 基本形
        'あけましておめでとう', 'あけましておめでとうございます', 'あけおめ', 'ことより','あけおめことよろ',
        '新年おめでとう', '新年おめでとうございます', '新年あけましておめでとう', '新年あけましておめでとうございます',
        '謹賀新年', 'きんがしんねん', '賀正', 'がしょう', '迎春', 'げいしゅん', '初春', 'しょしゅん',
        '良いお年を', 'よいおとしを', '良いお年をお迎えください', 'よいおとしをおむかえください',
        '良い年を', 'よいとしを', '良い年をお迎えください', 'よいとしをおむかえください',
        '新年', 'しんねん', '正月', 'しょうがつ', 'お正月', 'おしょうがつ',
        // 英語
        'happy new year', 'happy new year!', 'new year', 'newyear', 'happy new year to you',
        'wishing you a happy new year', 'new year greetings', 'new year wishes'
    ]),
    birthday: new Set([
        // 基本形
        '誕生日', 'たんじょうび', '誕生日です', 'たんじょうびです', '誕生日おめでとう',
        '誕生日おめでとうございます', '今日が誕生日', 'きょうがたんじょうび', '今日は誕生日', 'きょうはたんじょうび',
        'お誕生日', 'おたんじょうび', 'お誕生日おめでとう', 'おたんじょうびおめでとう',
        'お誕生日おめでとうございます', 'おたんじょうびおめでとうございます',
        'ハッピーバースデー', 'はっぴーばーすでー', 'ハッピーバースデイ', 'はっぴーばーすでい',
        // 英語
        'birthday', 'happy birthday', 'birthday!', 'my birthday', "it's my birthday",
        'happy birthday to you', 'birthday wishes', 'birthday greetings', 'happy bday', 'bday'
    ]),
    christmas: new Set([
        // 基本形
        'メリークリスマス', 'めりーくりすます', 'クリスマス', 'くりすます', 'クリスマスおめでとう',
        'クリスマスおめでとうございます', 'メリークリスマス！', 'クリスマスです', 'クリスマスだ',
        'メリークリスマス！', 'クリスマスイブ', 'くりすますいぶ', 'クリスマスイブです',
        'クリスマスおめでとうございます', 'クリスマスおめでとう', 'クリスマスです',
        'ハッピークリスマス', 'はっぴーくりすます', 'クリスマスおめでとうございます',
        // 英語
        'merry christmas', 'merry christmas!', 'christmas', 'xmas', 'happy christmas',
        'merry xmas', 'xmas!', 'christmas eve', 'happy holidays', 'season\'s greetings',
        'merry christmas to you', 'christmas wishes', 'christmas greetings'
    ]),
    halloween: new Set([
        // 基本形
        'ハッピーハロウィン', 'はっぴーはろうぃん', 'ハロウィン', 'はろうぃん', 'ハロウィンおめでとう',
        'ハロウィンです', 'ハロウィンだ', 'トリックオアトリート', 'とりっくおあとりーと',
        'トリック・オア・トリート', 'とりっくおあとりーと', 'ハロウィンおめでとうございます',
        // 英語
        'happy halloween', 'happy halloween!', 'halloween', 'trick or treat', 'trick or treat!',
        'trick-or-treat', 'happy halloween to you', 'halloween wishes', 'halloween greetings'
    ]),
    valentine: new Set([
        // 基本形
        'バレンタイン', 'ばれんたいん', 'バレンタインデー', 'ばれんたいんでー', 'バレンタインおめでとう',
        'バレンタインデーおめでとう', 'バレンタインです', 'バレンタインだ', 'ハッピーバレンタイン',
        'はっぴーばれんたいん', 'バレンタインおめでとうございます', 'バレンタインデーおめでとうございます',
        // 英語
        'valentine', 'valentine\'s day', 'happy valentine', 'happy valentine\'s day',
        'valentines day', 'valentine day', 'happy valentines', 'valentine wishes'
    ]),
    whiteDay: new Set([
        // 基本形
        'ホワイトデー', 'ほわいとでー', 'ホワイトデーおめでとう', 'ホワイトデーです', 'ホワイトデーだ',
        'ホワイトデーおめでとうございます', 'ハッピーホワイトデー', 'はっぴーほわいとでー',
        // 英語
        'white day', 'white day!', 'happy white day', 'white day wishes', 'white day greetings'
    ]),
    tanabata: new Set([
        // 基本形
        '七夕', 'たなばた', '七夕祭り', 'たなばたまつり', '七夕です', '七夕だ', '七夕おめでとう',
        '七夕おめでとうございます', '七夕の日', 'たなばたのひ', '星祭り', 'ほしまつり',
        // 英語
        'tanabata', 'star festival', 'tanabata festival', 'tanabata wishes', 'tanabata greetings'
    ]),
    obon: new Set([
        // 基本形
        'お盆', 'おぼん', 'お盆です', 'お盆だ', 'お盆休み', 'おぼんやすみ', 'お盆おめでとう',
        'お盆おめでとうございます', 'お盆の日', 'おぼんのひ', '盂蘭盆', 'うらぼん',
        // 英語
        'obon', 'bon festival', 'obon festival', 'obon wishes', 'obon greetings'
    ]),
    childrensDay: new Set([
        // 基本形
        'こどもの日', 'こどものひ', '子供の日', 'こどもの日おめでとう', 'こどもの日です', 'こどもの日だ',
        'こどもの日おめでとうございます', '子供の日おめでとう', '子供の日です', '子供の日だ',
        '子どもの日', 'こどもの日おめでとう', '子どもの日おめでとう',
        // 英語
        'children\'s day', 'kodomo no hi', 'childrens day', 'children day', 'children\'s day wishes'
    ]),
    mothersDay: new Set([
        // 基本形
        '母の日', 'ははのひ', '母の日おめでとう', '母の日です', '母の日だ', 'ハッピーマザーズデー',
        'はっぴーまざーずでー', '母の日おめでとうございます', 'お母さんの日', 'おかあさんのひ',
        // 英語
        'mother\'s day', 'mothers day', 'happy mother\'s day', 'mothersday', 'mother day',
        'mother\'s day wishes', 'mother\'s day greetings'
    ]),
    fathersDay: new Set([
        // 基本形
        '父の日', 'ちちのひ', '父の日おめでとう', '父の日です', '父の日だ', 'ハッピーファザーズデー',
        'はっぴーふぁざーずでー', '父の日おめでとうございます', 'お父さんの日', 'おとうさんのひ',
        // 英語
        'father\'s day', 'fathers day', 'happy father\'s day', 'fathersday', 'father day',
        'father\'s day wishes', 'father\'s day greetings'
    ]),
    respectForTheAgedDay: new Set([
        // 基本形
        '敬老の日', 'けいろうのひ', '敬老の日おめでとう', '敬老の日です', '敬老の日だ',
        '敬老の日おめでとうございます', 'けいろうのひおめでとう', 'けいろうのひです',
        // 英語
        'respect for the aged day', 'keiro no hi', 'respectfortheagedday', 'respect for aged day',
        'aged day', 'elderly day', 'senior citizens day'
    ]),
    newYearsEve: new Set([
        // 基本形
        '大晦日', 'おおみそか', '大晦日です', '大晦日だ', '大晦日おめでとう', '年越し', 'としこし',
        '年越しです', 'としこしです', '年越しだ', 'としこしだ', '除夜', 'じょや', '除夜の鐘', 'じょやのかね',
        '良いお年を', 'よいおとしを', '良いお年をお迎えください', 'よいおとしをおむかえください',
        // 英語
        'new year\'s eve', 'new years eve', 'newyearseve', 'year end', 'new year eve',
        'new year\'s eve wishes', 'new year\'s eve greetings', 'end of year'
    ])
};

// よく使われる絵文字のカスタムリスト（一般的な絵文字を広くカバー）
const EMOJI_LIST = [
    '🎉', '🎊', '🎈', '🎁', '⭐', '🌟', '✨', '💫', '🎯', '🎮', '🎲', '🎪', '🎭', '🎨', '🎬', '🎤', '🎧', '🎵', '🎶', '🎸', '🎹', '🎺', '🎻', '🥁', '🎷',
    '😄', '😊', '😃', '😁', '😆', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤗', '🤩', '🤔', '🤨', '😏', '😎', '🤓', '🧐', '😇', '🙂', '🙃', '😉', '😌',
    '😢', '😭', '😤', '😠', '😡', '🤬', '🤯', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴', '🤢', '🤮', '🤧', '😷', '🤒', '🤕', '🤑', '🤠',
    '😈', '👿', '👹', '👺', '🤡', '💩', '👻', '💀', '☠️', '👽', '👾', '🤖', '🎃',
    '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾',
    '👋', '🤚', '🖐', '✋', '🖖', '👌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏',
    '💪', '🦾', '🦿', '🦵', '🦶', '👂', '🦻', '👃', '🧠', '🦷', '🦴', '👀', '👁', '👅', '👄',
    '💋', '💘', '💝', '💖', '💗', '💓', '💞', '💕', '💟', '❣️', '💔', '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💯', '💢', '💥', '💫', '💦', '💨', '🕳️', '💣', '💬', '👁️‍🗨️', '🗨️', '🗯️', '💭', '💤'
];

// グローバルバッファ（Canvas最適化用）
let canvasBuffer = null;

// イースターエッグ実行中フラグ（同時実行防止）
let isEasterEggActive = false;

/**
 * メッセージ正規化（記号除去・小文字化）
 * 完全一致チェックのため、記号のみを除去し、空白は保持
 * @param {string} message - ユーザーメッセージ
 * @returns {string} 正規化されたメッセージ
 */
function normalizeMessage(message) {
    // 記号除去のみ、小文字化は英語のみ
    let normalized = message.trim();
    
    // 末尾の空白、感嘆符、句点、疑問符などを除去（完全一致のため）
    normalized = normalized.replace(/[！。？!?.。、,，]+$/g, '');
    
    // 先頭・末尾の空白を除去（ただし、語間の空白は保持）
    normalized = normalized.trim();
    
    // 英語の場合は小文字化（日本語はそのまま）
    // 複数語の英語トリガーに対応するため、空白を含む英語も小文字化
    if (/^[a-zA-Z\s!?.]+$/.test(normalized)) {
        normalized = normalized.toLowerCase();
        // 複数の空白を1つに統一（完全一致のため）
        normalized = normalized.replace(/\s+/g, ' ');
    }
    
    return normalized;
}

/**
 * 否定語の検出
 * @param {string} message - ユーザーメッセージ
 * @returns {boolean} 否定語が検出された場合true
 */
function checkNegation(message) {
    // 否定助動詞の検出
    const negationAuxiliaries = /(ない|ず|ぬ|ん|ません|ませんでした)/;
    
    // 否定表現パターン
    const negationPatterns = [
        /(治っていない|良くならない|改善しない|回復しない)/,
        /(〜ていない|〜ない|〜ずに)/
    ];
    
    return negationAuxiliaries.test(message) || 
           negationPatterns.some(pattern => pattern.test(message));
}

/**
 * 医療用語チェック（厳格モード、早期リターン）
 * 1語でも検出したら即座にtrueを返す
 * @param {string} message - ユーザーメッセージ
 * @returns {boolean} 医療用語が含まれている場合true
 */
function checkMedicalTerms(message) {
    if (!message || message.trim().length === 0) {
        return false;
    }
    
    // 単語に分割（空白、句読点で分割）
    // 日本語と英語の両方に対応
    const words = message.split(/[\s、。，．,.\s]+/).filter(word => word.length > 0);
    
    // 早期リターン: 1語でも検出したら即座にtrue
    for (const word of words) {
        // 完全一致チェック（高速）
        if (MEDICAL_TERMS.has(word)) {
            return true; // 即座に通常処理へ
        }
        
        // 部分一致もチェック（より確実に検出、ただしパフォーマンスを考慮）
        // 例：「頭痛が」→「頭痛」を検出
        // ただし、短い単語（2文字以下）はスキップしてパフォーマンスを維持
        // また、医療用語リストが大きいため、早期にマッチしたら即座にリターン
        if (word.length >= 2) {
            for (const medicalTerm of MEDICAL_TERMS) {
                if (medicalTerm.length >= 2) {
                    // 部分一致チェック（wordにmedicalTermが含まれる、またはその逆）
                    if (word.includes(medicalTerm) || medicalTerm.includes(word)) {
                        return true; // 即座に通常処理へ
                    }
                }
            }
        }
    }
    
    return false;
}

/**
 * Unicode絵文字の範囲を定義（Unicode 16.0 / Emoji 16.1準拠）
 * 包括的な絵文字検出のための正規表現パターン
 */
const EMOJI_PATTERN = /[\u{1F300}-\u{1F9FF}]|[\u{1FA00}-\u{1FAFF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F900}-\u{1F9FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F700}-\u{1F77F}]|[\u{1F780}-\u{1F7FF}]|[\u{1F800}-\u{1F8FF}]|[\u{1F900}-\u{1F9FF}]|[\u{1FA00}-\u{1FA6F}]|[\u{1FA70}-\u{1FAFF}]|[\u{200D}]|[\u{20E3}]|[\u{FE0F}]|[\u{FE00}-\u{FE0F}]/gu;

/**
 * 文字が絵文字かどうかを判定
 * @param {string} char - 判定する文字
 * @returns {boolean} 絵文字の場合true
 */
function isEmojiChar(char) {
    // Unicode絵文字の範囲をチェック
    // 基本多言語面（BMP）の絵文字
    const codePoint = char.codePointAt(0);
    if (!codePoint) return false;
    
    // 絵文字の主要なUnicode範囲
    if (
        (codePoint >= 0x1F300 && codePoint <= 0x1F9FF) || // その他の記号・絵文字
        (codePoint >= 0x1FA00 && codePoint <= 0x1FAFF) || // 拡張A
        (codePoint >= 0x2600 && codePoint <= 0x26FF) ||   // その他の記号
        (codePoint >= 0x2700 && codePoint <= 0x27BF) ||   // 装飾記号
        (codePoint >= 0x1F600 && codePoint <= 0x1F64F) || // 顔文字
        (codePoint >= 0x1F680 && codePoint <= 0x1F6FF) || // 交通・地図記号
        (codePoint >= 0x1F700 && codePoint <= 0x1F77F) || // その他の記号
        (codePoint >= 0x1F780 && codePoint <= 0x1F7FF) || // その他の記号
        (codePoint >= 0x1F800 && codePoint <= 0x1F8FF) || // その他の記号
        (codePoint >= 0x1F900 && codePoint <= 0x1F9FF) || // 補助記号・絵文字
        (codePoint >= 0x1FA00 && codePoint <= 0x1FA6F) || // 拡張A
        (codePoint >= 0x1FA70 && codePoint <= 0x1FAFF) || // 拡張A
        (codePoint >= 0x1F1E0 && codePoint <= 0x1F1FF)    // 地域指標記号
    ) {
        return true;
    }
    
    // 修飾子や結合文字（ゼロ幅結合子など）は除外
    if (codePoint === 0x200D || codePoint === 0xFE0F || codePoint === 0xFE00) {
        return false;
    }
    
    return false;
}

/**
 * メッセージから絵文字を抽出
 * Unicode 16.0 / Emoji 16.1準拠の包括的な抽出
 * @param {string} message - ユーザーメッセージ
 * @returns {string[]} 抽出された絵文字の配列
 */
function extractEmojis(message) {
    const emojis = [];
    const cleaned = message.trim().replace(/[\s！。？!?.。、,，\s]/g, '');
    
    if (cleaned.length === 0) return [];
    
    // Unicode絵文字の正規表現を使用して抽出（最初の試行）
    const emojiMatches = cleaned.match(EMOJI_PATTERN);
    if (emojiMatches) {
        emojis.push(...emojiMatches);
    }
    
    // より包括的な検出：文字列を反復して絵文字を検出
    let i = 0;
    while (i < cleaned.length) {
        const char = cleaned[i];
        const codePoint = char.codePointAt(0);
        
        if (!codePoint) {
            i++;
            continue;
        }
        
        // サロゲートペア（2文字で1つの絵文字）を処理
        if (codePoint >= 0xD800 && codePoint <= 0xDBFF && i + 1 < cleaned.length) {
            const nextChar = cleaned[i + 1];
            const nextCodePoint = nextChar.codePointAt(0);
            if (nextCodePoint && nextCodePoint >= 0xDC00 && nextCodePoint <= 0xDFFF) {
                const surrogatePair = char + nextChar;
                const pairCodePoint = surrogatePair.codePointAt(0);
                
                // サロゲートペアのコードポイントで絵文字範囲をチェック
                if (pairCodePoint && (
                    (pairCodePoint >= 0x1F300 && pairCodePoint <= 0x1F9FF) ||
                    (pairCodePoint >= 0x1FA00 && pairCodePoint <= 0x1FAFF) ||
                    (pairCodePoint >= 0x1F600 && pairCodePoint <= 0x1F64F) ||
                    (pairCodePoint >= 0x1F680 && pairCodePoint <= 0x1F6FF) ||
                    (pairCodePoint >= 0x1F700 && pairCodePoint <= 0x1F77F) ||
                    (pairCodePoint >= 0x1F780 && pairCodePoint <= 0x1F7FF) ||
                    (pairCodePoint >= 0x1F800 && pairCodePoint <= 0x1F8FF) ||
                    (pairCodePoint >= 0x1F900 && pairCodePoint <= 0x1F9FF) ||
                    (pairCodePoint >= 0x1FA00 && pairCodePoint <= 0x1FA6F) ||
                    (pairCodePoint >= 0x1FA70 && pairCodePoint <= 0x1FAFF) ||
                    (pairCodePoint >= 0x1F1E0 && pairCodePoint <= 0x1F1FF)
                )) {
                    emojis.push(surrogatePair);
                    i += 2; // サロゲートペアなので2文字進む
                    continue;
                }
            }
        }
        
        // 単一文字の絵文字をチェック
        if (isEmojiChar(char)) {
            emojis.push(char);
        }
        
        i++;
    }
    
    // 重複を除去し、空の要素を除外
    return [...new Set(emojis)].filter(emoji => emoji && emoji.length > 0);
}

/**
 * 絵文字のみのメッセージかチェック
 * @param {string} message - ユーザーメッセージ（正規化前の元のメッセージ）
 * @returns {boolean} 絵文字のみの場合true
 */
function isEmojiOnly(message) {
    const trimmed = message.trim();
    if (trimmed.length === 0) return false;
    
    // 空白や記号を除外
    const cleaned = trimmed.replace(/[\s！。？!?.。、,，\s]/g, '');
    if (cleaned.length === 0) return false;
    
    // 絵文字を抽出
    const emojis = extractEmojis(cleaned);
    
    // 抽出された絵文字の長さの合計が、クリーンアップ後の文字列の長さと一致するかチェック
    // （絵文字は複数文字で構成される場合があるため、概算でチェック）
    const emojiLength = emojis.join('').length;
    const cleanedLength = cleaned.length;
    
    // 絵文字が存在し、かつ絵文字の長さがクリーンアップ後の文字列の大部分を占めている場合
    return emojis.length > 0 && emojiLength >= cleanedLength * 0.8;
}

/**
 * イースターエッグトリガーのマッチング
 * @param {string} normalized - 正規化されたメッセージ
 * @returns {string|null} マッチしたトリガーの種類、マッチしない場合はnull
 */
function matchEasterEggTriggers(normalized) {
    // 感謝メッセージ
    if (THANKS_TRIGGERS.has(normalized)) {
        return 'thanks';
    }
    
    // 画面変形系
    for (const [type, triggers] of Object.entries(TRANSFORM_TRIGGERS)) {
        if (triggers.has(normalized)) {
            return type;
        }
    }
    
    // ゲーム系
    if (GAME_TRIGGERS.snake.has(normalized)) {
        return 'snake';
    }
    
    // 絵文字のみのチェックは正規化前のメッセージで実施するため、ここではスキップ
    
    // アニメーション系
    for (const [type, triggers] of Object.entries(ANIMATION_TRIGGERS)) {
        if (triggers.has(normalized)) {
            return type;
        }
    }
    
    // 特別イベント系
    for (const [type, triggers] of Object.entries(SPECIAL_EVENT_TRIGGERS)) {
        if (triggers.has(normalized)) {
            return type;
        }
    }
    
    return null;
}

/**
 * ログ記録（標準レベル）
 * @param {string} trigger - 発動トリガー
 * @param {string} message - ユーザーメッセージ
 * @param {number} processingTime - 処理時間（ミリ秒）
 */
function logEasterEgg(trigger, message, processingTime = null) {
    const timestamp = new Date().toISOString();
    const logEntry = {
        timestamp,
        trigger,
        message: message.substring(0, 100), // サニタイズ（長さ制限）
        processingTime
    };
    
    console.log(`[EasterEgg] ${JSON.stringify(logEntry)}`);
    
    // サーバーへのログ送信（オプション、後で実装可能）
    // fetch('/api/log-easter-egg', { method: 'POST', body: JSON.stringify(logEntry) });
}

/**
 * エラーログ記録（完全なデバッグ情報）
 * @param {Error} error - エラーオブジェクト
 * @param {string} context - コンテキスト情報
 * @param {object} additionalInfo - 追加情報
 */
function logEasterEggError(error, context, additionalInfo = {}) {
    const debugInfo = {
        timestamp: new Date().toISOString(),
        error: {
            message: error.message,
            stack: error.stack,
            name: error.name
        },
        context,
        additionalInfo,
        environment: {
            userAgent: navigator.userAgent,
            screenSize: `${window.innerWidth}x${window.innerHeight}`,
            devicePixelRatio: window.devicePixelRatio || 1
        }
    };
    
    console.error('[EasterEgg Error]', JSON.stringify(debugInfo, null, 2));
}

/**
 * メイン判定関数
 * 処理順序: Normalization → Medical/Negation Check → Easter Egg Match
 * @param {string} message - ユーザーメッセージ
 * @returns {boolean} イースターエッグが発動した場合true
 */
function checkEasterEggs(message) {
    // 同時実行防止
    if (isEasterEggActive) {
        return false;
    }
    
    const startTime = performance.now();
    
    try {
        // Step 1: Normalization（記号除去・小文字化）
        const normalized = normalizeMessage(message);
        
        // Step 2: Medical/Negation Check（早期リターン）
        // 医療用語チェックは正規化前のメッセージでも実施（より確実に検出）
        if (checkMedicalTerms(message) || checkMedicalTerms(normalized)) {
            // 医療用語が1語でも含まれていれば即座に通常処理へ
            return false;
        }
        
        if (checkNegation(normalized)) {
            // 否定語が検出されれば即座に通常処理へ
            return false;
        }
        
        // Step 3: Easter Egg Match（最後にトリガーワードと比較）
        // 絵文字のみのチェックは正規化前のメッセージで実施
        let trigger = matchEasterEggTriggers(normalized);
        
        // デバッグログ（開発時のみ）
        if (trigger) {
            console.log('[EasterEgg] Trigger matched:', trigger, 'Normalized:', normalized, 'Original:', message);
        }
        
        // 絵文字のみの場合は正規化前のメッセージで再チェック
        if (!trigger && isEmojiOnly(message)) {
            const processingTime = performance.now() - startTime;
            logEasterEgg('emoji', message, processingTime);
            
            // ユーザーメッセージをチャットに表示
            if (typeof window.addUserMessage === 'function') {
                window.addUserMessage(message);
            }
            
            // 適切な返信を生成してチャットに表示
            const responseMessage = getEasterEggResponse('emoji', message);
            if (typeof window.addMessage === 'function') {
                setTimeout(() => {
                    window.addMessage(responseMessage, 'bot');
                    if (typeof window.scrollToBottom === 'function') {
                        window.scrollToBottom();
                    }
                }, 100);
            }
            
            // 絵文字のパーティクル効果を実行
            setTimeout(() => {
                createEmojiParticleEffect(message);
            }, 200);
            
            // 通常処理をスキップ
            return true;
        }
        
        if (trigger) {
            // 感謝系の場合は通常処理に流す（アニメーションのみ実行）
            if (trigger === 'thanks') {
                const processingTime = performance.now() - startTime;
                logEasterEgg(trigger, message, processingTime);
                
                // パーティクル効果を実行（モーダルは表示しない）
                // 少し遅延させて通常処理の後に実行
                setTimeout(() => {
                    createParticleEffect();
                }, 100);
                
                // 通常処理に流すためfalseを返す
                return false;
            }
            
            // その他のトリガーは適切な返信を表示してから実行
            isEasterEggActive = true;
            const processingTime = performance.now() - startTime;
            logEasterEgg(trigger, message, processingTime);
            
            // ユーザーメッセージをチャットに表示
            if (typeof window.addUserMessage === 'function') {
                window.addUserMessage(message);
            }
            
            // 適切な返信を生成してチャットに表示
            const responseMessage = getEasterEggResponse(trigger, message);
            if (typeof window.addMessage === 'function') {
                setTimeout(() => {
                    window.addMessage(responseMessage, 'bot');
                    if (typeof window.scrollToBottom === 'function') {
                        window.scrollToBottom();
                    }
                }, 100);
            }
            
            // トリガーに応じた処理を実行
            if (trigger === 'fireworks' || trigger === 'snow' || trigger === 'rain' || 
                trigger === 'newyear' || trigger === 'birthday' || trigger === 'christmas' ||
                trigger === 'halloween' || trigger === 'valentine' || trigger === 'whiteDay' ||
                trigger === 'tanabata' || trigger === 'obon' || trigger === 'childrensDay' ||
                trigger === 'mothersDay' || trigger === 'fathersDay' || trigger === 'respectForTheAgedDay' ||
                trigger === 'newYearsEve') {
                // アニメーション系は少し遅延させて実行
                setTimeout(() => {
                    executeEasterEgg(trigger, message);
                }, 200);
            } else if (trigger === 'rotate' || trigger === 'skew' || trigger === 'shake' || 
                       trigger === 'zoom' || trigger === 'flip' || trigger === 'bounce' || 
                       trigger === 'pulse' || trigger === 'glow') {
                // 画面変形系も少し遅延させて実行（チャット表示を確実にするため）
                setTimeout(() => {
                    executeEasterEgg(trigger, message);
                }, 200);
            } else {
                // ゲーム系（snake）は即座に実行
                executeEasterEgg(trigger, message);
            }
            
            return true;
        }
        
        return false;
    } catch (error) {
        logEasterEggError(error, 'checkEasterEggs', { message });
        return false;
    }
}

/**
 * イースターエッグに応じた返信メッセージを生成（ランダム）
 * @param {string} trigger - トリガーの種類
 * @param {string} message - ユーザーメッセージ
 * @returns {string} 返信メッセージ
 */
function getEasterEggResponse(trigger, message) {
    // 現在の言語を取得
    const currentLang = typeof currentLanguage !== 'undefined' ? currentLanguage : 'ja';
    const t = typeof translations !== 'undefined' && translations[currentLang] ? translations[currentLang] : {};
    
    // ランダムな返信を生成するための配列
    const responses = {
        rotate: [
            '🎠 画面が回転しました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「スネーク」と入力するとゲームが遊べたり、「花火」と入力すると花火が表示されたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。',
            '🎡 回転しました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「傾く」「揺れる」で画面が変形します\n\n症状についてのご相談も、いつでもお気軽にどうぞ！',
            '🎪 回転しました！\n\nこのアプリは「チャット型医薬品相談ツール」です。症状を教えていただくと、AIが適切な市販薬の候補をご提案します。\n\n他にも「雪」「雨」「花火」などのキーワードでアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！'
        ],
        skew: [
            '🎨 画面が傾きました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「雪」「雨」「花火」などのキーワードでアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🎭 傾きました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n\nぜひ色々な機能をお試しください！',
            '🎪 画面が傾きました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「回転」と入力すると画面が回転したり、「揺れる」と入力すると画面が揺れたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        shake: [
            '📱 画面が揺れました！\n\nこのアプリには、遊園地のような楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 年齢やアレルギー情報を登録すると、より安全な提案が可能\n• 薬剤師要請機能（将来的な実装を想定）\n\nぜひ色々な機能をお試しください！',
            '🎢 揺れました！\n\nこのアプリは「チャット型医薬品相談ツール」です。症状を教えていただくと、AIが適切な市販薬の候補をご提案します。\n\n他にも「回転」「傾く」で画面が変形したり、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりします。ぜひ色々試してみてください！',
            '🎡 画面が揺れました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「拡大」「反転」「バウンス」で画面が変形します\n\n症状についてのご相談も、いつでもお気軽にどうぞ！'
        ],
        zoom: [
            '🔍 画面が拡大しました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「回転」「傾く」「揺れる」「反転」「バウンス」などで画面が変形したり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🔎 拡大しました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「揺れる」「反転」「バウンス」「脈動」「光る」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '🔍 画面が拡大しました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「縮小」と入力すると画面が縮小したり、「反転」で画面が反転したりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        flip: [
            '🔄 画面が反転しました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「回転」「傾く」「揺れる」「拡大」「バウンス」などで画面が変形したり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🪞 反転しました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「揺れる」「拡大」「バウンス」「脈動」「光る」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '🔄 画面が反転しました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「回転」と入力すると画面が回転したり、「拡大」で画面が拡大したりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        bounce: [
            '⚽ 画面がバウンスしました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「回転」「傾く」「揺れる」「拡大」「反転」などで画面が変形したり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🏀 バウンスしました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「揺れる」「拡大」「反転」「脈動」「光る」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '⚽ 画面がバウンスしました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「跳ねる」と入力すると画面が跳ねたり、「脈動」で画面が脈動したりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        pulse: [
            '💓 画面が脈動しました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「回転」「傾く」「揺れる」「拡大」「反転」「バウンス」などで画面が変形したり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '💗 脈動しました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「揺れる」「拡大」「反転」「バウンス」「光る」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '💓 画面が脈動しました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「光る」と入力すると画面が光ったり、「バウンス」で画面が跳ねたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        glow: [
            '✨ 画面が光りました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「回転」「傾く」「揺れる」「拡大」「反転」「バウンス」「脈動」などで画面が変形したり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🌟 光りました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「揺れる」「拡大」「反転」「バウンス」「脈動」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '✨ 画面が光りました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「輝く」と入力すると画面が輝いたり、「脈動」で画面が脈動したりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        snake: [
            '🐍 スネークゲームを起動しました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\nゲームを楽しんだ後は、ぜひ症状についてのご相談もお聞かせください。',
            '🎮 スネークゲームを起動しました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「花火」「雪」「雨」でアニメーションが表示されます\n• 「回転」「傾く」「揺れる」で画面が変形します\n\nゲームを楽しんだ後は、ぜひ症状についてのご相談もお聞かせください！',
            '🐍 スネークゲームを起動しました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「花火」と入力すると花火が表示されたり、「雪」「雨」でアニメーションが表示されたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        emoji: [
            '✨ 素敵な絵文字ですね！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「雪」「雨」「花火」などのキーワードでアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🎉 素敵な絵文字ですね！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「花火」「雪」「雨」でアニメーションが表示されます\n\nぜひ色々な機能をお試しください！',
            '🌟 素敵な絵文字ですね！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「スネーク」と入力するとゲームが遊べたり、「回転」「傾く」「揺れる」で画面が変形したりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        fireworks: [
            '🎆 花火が上がりました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「雪」「雨」などのキーワードでアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🎇 花火が上がりました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「回転」「傾く」「揺れる」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '🎆 花火が上がりました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「雪」「雨」と入力するとアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        snow: [
            '❄️ 雪が降りました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「雨」「花火」などのキーワードでアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '❅ 雪が降りました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「回転」「傾く」「揺れる」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '❄️ 雪が降りました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「雨」「花火」と入力するとアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        rain: [
            '🌧️ 雨が降りました！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n他にも「雪」「花火」などのキーワードでアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ色々試してみてください！',
            '🌦️ 雨が降りました！\n\n遊園地のように、このアプリにも楽しい機能がたくさん隠れています。\n\n主な機能：\n• 症状を入力すると、AIが適切な市販薬を提案\n• 「スネーク」でゲームが遊べます\n• 「回転」「傾く」「揺れる」で画面が変形します\n\nぜひ色々な機能をお試しください！',
            '🌧️ 雨が降りました！\n\nこのアプリには、他にも面白い機能が隠れています。例えば「雪」「花火」と入力するとアニメーションが表示されたり、「スネーク」でゲームが遊べたりします。ぜひ試してみてください！\n\nもちろん、症状についてのご相談もいつでもお受けしています。'
        ],
        newyear: [
            '🎊 あけましておめでとうございます！\n\n新年を迎えられたことを心よりお祝い申し上げます。今年も健康で素晴らしい一年になりますように！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n今年もどうぞよろしくお願いいたします！',
            '🎉 新年あけましておめでとうございます！\n\n新しい年が皆様にとって健康で幸せな一年になりますように。\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n今年もよろしくお願いいたします！',
            '🎈 あけましておめでとうございます！\n\n新年を迎えられたことをお祝い申し上げます。今年も健康で素晴らしい一年になりますように！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        birthday: [
            '🎂 お誕生日おめでとうございます！\n\n素晴らしい一年になりますように、心よりお祝い申し上げます！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n健康で幸せな一年になりますように！',
            '🎁 お誕生日おめでとうございます！\n\n素敵な一年になりますように、心よりお祝い申し上げます！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしい一年になりますように！',
            '🎉 お誕生日おめでとうございます！\n\n健康で幸せな一年になりますように、心よりお祝い申し上げます！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        christmas: [
            '🎄 メリークリスマス！\n\n素敵なクリスマスをお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしいクリスマスと良いお年をお迎えください！',
            '🎅 メリークリスマス！\n\nクリスマスの素敵なひとときをお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしいクリスマスをお過ごしください！',
            '🎁 メリークリスマス！\n\n素敵なクリスマスをお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        halloween: [
            '🎃 ハッピーハロウィン！\n\n楽しいハロウィンをお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\nトリックオアトリート！',
            '👻 ハッピーハロウィン！\n\n楽しいハロウィンをお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\nトリックオアトリート！',
            '🦇 ハッピーハロウィン！\n\n楽しいハロウィンをお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        valentine: [
            '💝 ハッピーバレンタイン！\n\n素敵なバレンタインデーをお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしいバレンタインデーをお過ごしください！',
            '💕 ハッピーバレンタイン！\n\n素敵なバレンタインデーをお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしいバレンタインデーをお過ごしください！',
            '💖 ハッピーバレンタイン！\n\n素敵なバレンタインデーをお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        whiteDay: [
            '🤍 ハッピーホワイトデー！\n\n素敵なホワイトデーをお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしいホワイトデーをお過ごしください！',
            '💝 ハッピーホワイトデー！\n\n素敵なホワイトデーをお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしいホワイトデーをお過ごしください！',
            '🎁 ハッピーホワイトデー！\n\n素敵なホワイトデーをお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        tanabata: [
            '🎋 七夕おめでとうございます！\n\n素敵な七夕をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n願い事が叶いますように！',
            '⭐ 七夕おめでとうございます！\n\n素敵な七夕をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n願い事が叶いますように！',
            '✨ 七夕おめでとうございます！\n\n素敵な七夕をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        obon: [
            '🕯️ お盆おめでとうございます！\n\n素敵なお盆をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしいお盆をお過ごしください！',
            '🏮 お盆おめでとうございます！\n\n素敵なお盆をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしいお盆をお過ごしください！',
            '🎐 お盆おめでとうございます！\n\n素敵なお盆をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        childrensDay: [
            '🎏 こどもの日おめでとうございます！\n\n素敵なこどもの日をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしいこどもの日をお過ごしください！',
            '🎎 こどもの日おめでとうございます！\n\n素敵なこどもの日をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしいこどもの日をお過ごしください！',
            '🎌 こどもの日おめでとうございます！\n\n素敵なこどもの日をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        mothersDay: [
            '💐 母の日おめでとうございます！\n\n素敵な母の日をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしい母の日をお過ごしください！',
            '🌷 母の日おめでとうございます！\n\n素敵な母の日をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしい母の日をお過ごしください！',
            '🌹 母の日おめでとうございます！\n\n素敵な母の日をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        fathersDay: [
            '👔 父の日おめでとうございます！\n\n素敵な父の日をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしい父の日をお過ごしください！',
            '🎁 父の日おめでとうございます！\n\n素敵な父の日をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしい父の日をお過ごしください！',
            '🍺 父の日おめでとうございます！\n\n素敵な父の日をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        respectForTheAgedDay: [
            '👴 敬老の日おめでとうございます！\n\n素敵な敬老の日をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n素晴らしい敬老の日をお過ごしください！',
            '👵 敬老の日おめでとうございます！\n\n素敵な敬老の日をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n素晴らしい敬老の日をお過ごしください！',
            '🌻 敬老の日おめでとうございます！\n\n素敵な敬老の日をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ],
        newYearsEve: [
            '🎊 大晦日おめでとうございます！\n\n素敵な大晦日をお過ごしください！\n\nこのアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n良いお年をお迎えください！',
            '🎉 大晦日おめでとうございます！\n\n素敵な大晦日をお過ごしください！\n\nこのアプリでは、症状を入力するとAIが適切な市販薬を提案します。また、「スネーク」でゲームが遊べたり、「花火」「雪」「雨」でアニメーションが表示されたりする楽しい機能も隠れています。\n\n良いお年をお迎えください！',
            '🎈 大晦日おめでとうございます！\n\n素敵な大晦日をお過ごしください！\n\n症状についてのご相談も、いつでもお気軽にお聞かせください。'
        ]
    };
    
    const triggerResponses = responses[trigger];
    if (triggerResponses && triggerResponses.length > 0) {
        // ランダムに返信を選択
        const randomIndex = Math.floor(Math.random() * triggerResponses.length);
        return triggerResponses[randomIndex];
    }
    
    // デフォルトの返信
    return 'こんにちは！このアプリは、チャット形式で症状を教えていただくと、AIが適切な市販薬の候補をご提案する「チャット型医薬品相談ツール」です。\n\n症状についてお聞かせください。';
}

/**
 * イースターエッグの実行
 * @param {string} trigger - トリガーの種類
 * @param {string} message - ユーザーメッセージ
 */
async function executeEasterEgg(trigger, message) {
    try {
        switch (trigger) {
            case 'thanks':
                // 感謝系は通常処理に流すため、ここには来ない
                // 念のため何もしない（既にcheckEasterEggsで処理済み）
                break;
            case 'rotate':
                triggerRotation();
                break;
            case 'skew':
                triggerSkew();
                break;
            case 'shake':
                triggerShake();
                break;
            case 'zoom':
                triggerZoom();
                break;
            case 'flip':
                triggerFlip();
                break;
            case 'bounce':
                triggerBounce();
                break;
            case 'pulse':
                triggerPulse();
                break;
            case 'glow':
                triggerGlow();
                break;
            case 'snake':
                await triggerSnakeGame();
                break;
            case 'fireworks':
                triggerFireworks();
                break;
            case 'snow':
                triggerSnow();
                break;
            case 'rain':
                triggerRain();
                break;
            case 'newyear':
                triggerNewYear();
                break;
            case 'birthday':
                triggerBirthday();
                break;
            case 'christmas':
                triggerChristmas();
                break;
            case 'halloween':
                triggerHalloween();
                break;
            case 'valentine':
                triggerValentine();
                break;
            case 'whiteDay':
                triggerWhiteDay();
                break;
            case 'tanabata':
                triggerTanabata();
                break;
            case 'obon':
                triggerObon();
                break;
            case 'childrensDay':
                triggerChildrensDay();
                break;
            case 'mothersDay':
                triggerMothersDay();
                break;
            case 'fathersDay':
                triggerFathersDay();
                break;
            case 'respectForTheAgedDay':
                triggerRespectForTheAgedDay();
                break;
            case 'newYearsEve':
                triggerNewYearsEve();
                break;
            default:
                console.warn(`[EasterEgg] Unknown trigger: ${trigger}`);
        }
    } catch (error) {
        logEasterEggError(error, 'executeEasterEgg', { trigger, message });
        isEasterEggActive = false;
    }
}

/**
 * イースターエッグの終了処理
 */
function finishEasterEgg() {
    isEasterEggActive = false;
}

/**
 * 感謝系のパーティクル効果のみ実行（モーダルは表示しない）
 * この関数は通常処理に流した後に呼び出される
 * 注意: この関数は現在使用されていない（checkEasterEggs内で直接createParticleEffectを呼び出している）
 */
function triggerThanksAnimation() {
    try {
        // パーティクル効果のみ実行（モーダルは表示しない）
        createParticleEffect();
        
        // 3秒後に自動停止
        setTimeout(() => {
            stopParticleEffect();
        }, 3000);
    } catch (error) {
        logEasterEggError(error, 'triggerThanksAnimation', {});
    }
}

/** 装飾パーティクル用スケール（短辺 640px 前後を 1.0、狭い画面で縮小・広い画面でやや拡大） */
function eggParticleScale() {
    if (typeof window === 'undefined') return 1;
    const v = Math.min(window.innerWidth || 640, window.innerHeight || 640);
    return Math.min(1.22, Math.max(0.66, v / 640));
}

function eggPx(value) {
    return Math.round(Number(value) * eggParticleScale());
}

/**
 * パーティクル効果（花びら・星）
 */
function createParticleEffect() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const particleContainer = document.createElement('div');
    particleContainer.id = 'easterEggParticles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(particleContainer);
    
    const particles = ['🌸', '✨', '⭐', '🌟', '💫'];
    const particleCount = window.innerWidth < 768 ? 20 : 30; // モバイルでは固定削減
    const ps = eggParticleScale();
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.textContent = particles[Math.floor(Math.random() * particles.length)];
        particle.style.cssText = `
            position: absolute;
            font-size: ${eggPx(20 + Math.random() * 20)}px;
            left: ${Math.random() * 100}%;
            top: ${-eggPx(20)}px;
            animation: particleFall ${2 + Math.random() * 2}s linear forwards;
            animation-delay: ${Math.random() * 1}s;
            opacity: 0.8;
        `;
        particleContainer.appendChild(particle);
    }
    
    // CSSアニメーションを追加
    if (!document.getElementById('easterEggParticleStyles')) {
        const style = document.createElement('style');
        style.id = 'easterEggParticleStyles';
        style.textContent = `
            @keyframes particleFall {
                0% {
                    transform: translateY(0) rotate(0deg);
                    opacity: 0.8;
                }
                100% {
                    transform: translateY(100vh) rotate(360deg);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 絵文字のパーティクル効果（入力された絵文字を使用）
 * Unicode 16.0 / Emoji 16.1準拠の包括的な対応
 * @param {string} message - ユーザーメッセージ（絵文字のみ）
 */
function createEmojiParticleEffect(message) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const particleContainer = document.createElement('div');
    particleContainer.id = 'easterEggEmojiParticles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(particleContainer);
    
    // メッセージから絵文字を抽出（Unicode範囲を使用）
    const emojis = extractEmojis(message);
    
    // 絵文字が抽出できない場合はデフォルトの絵文字を使用
    const particles = emojis.length > 0 ? emojis : ['🎉', '✨', '⭐'];
    const particleCount = window.innerWidth < 768 ? 25 : 40; // パーティクル数を増加
    const ps = eggParticleScale();
    
    // 各絵文字の出現頻度を計算（入力された絵文字の比率を反映）
    const emojiFrequency = {};
    particles.forEach(emoji => {
        emojiFrequency[emoji] = (emojiFrequency[emoji] || 0) + 1;
    });
    
    // パーティクルを生成
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        // 出現頻度に基づいて絵文字を選択（より多く入力された絵文字が多く表示される）
        const selectedEmoji = particles[Math.floor(Math.random() * particles.length)];
        particle.textContent = selectedEmoji;
        
        // 絵文字の種類に応じてサイズや速度を調整
        const isHeart = /[💘💓💕💖💗💝💞💟❤️🧡💛💚💙💜🖤🤍🤎💔❣️]/.test(selectedEmoji);
        const isFace = /[😀😁😂😃😄😅😆😇😈😉😊😋😌😍😎😏😐😑😒😓😔😕😖😗😘😙😚😛😜😝😞😟😠😡😢😣😤😥😦😧😨😩😪😫😬😭😮😯😰😱😲😳😴😵😶😷😸😹😺😻😼😽😾😿🙀]/.test(selectedEmoji);
        const isCharacter = /[👿👹👺👽👻💀☠️👾🤖🎃]/.test(selectedEmoji);
        
        // 絵文字の種類に応じたパラメータ
        let fontSize, duration, rotation, opacity;
        if (isHeart) {
            // ハートマークはゆっくりと上昇
            fontSize = 25 + Math.random() * 25;
            duration = 3 + Math.random() * 2;
            rotation = 180; // 半分だけ回転
            opacity = 0.9;
        } else if (isFace) {
            // 顔文字は弾けるような動き
            fontSize = 30 + Math.random() * 30;
            duration = 2 + Math.random() * 1.5;
            rotation = 360;
            opacity = 0.85;
        } else if (isCharacter) {
            // キャラクターは大きく表示
            fontSize = 35 + Math.random() * 25;
            duration = 2.5 + Math.random() * 2;
            rotation = 360;
            opacity = 0.9;
        } else {
            // その他の絵文字
            fontSize = 20 + Math.random() * 25;
            duration = 2 + Math.random() * 2;
            rotation = 360;
            opacity = 0.8;
        }
        fontSize = eggPx(fontSize);
        
        particle.style.cssText = `
            position: absolute;
            font-size: ${fontSize}px;
            left: ${Math.random() * 100}%;
            top: ${-eggPx(50)}px;
            animation: emojiParticleFall${i} ${duration}s linear forwards;
            animation-delay: ${Math.random() * 1.5}s;
            opacity: ${opacity};
            filter: drop-shadow(0 0 3px rgba(255, 255, 255, 0.5));
        `;
        particleContainer.appendChild(particle);
        
        // 各パーティクルに個別のアニメーションを設定
        const style = document.createElement('style');
        style.id = `emojiParticleStyle${i}`;
        const horizontalDrift = (Math.random() - 0.5) * 100 * ps;
        style.textContent = `
            @keyframes emojiParticleFall${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg) scale(0.8);
                    opacity: ${opacity};
                }
                50% {
                    transform: translateY(50vh) translateX(${horizontalDrift * 0.5}px) rotate(${rotation * 0.5}deg) scale(1.1);
                    opacity: ${opacity * 0.9};
                }
                100% {
                    transform: translateY(calc(100vh + ${eggPx(50)}px)) translateX(${horizontalDrift}px) rotate(${rotation}deg) scale(0.6);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // 4秒後に自動停止
    setTimeout(() => {
        stopEmojiParticleEffect();
        // 個別のスタイルも削除
        for (let i = 0; i < particleCount; i++) {
            const style = document.getElementById(`emojiParticleStyle${i}`);
            if (style) style.remove();
        }
    }, 4000);
}

/**
 * 絵文字パーティクル効果の停止
 */
function stopEmojiParticleEffect() {
    const container = document.getElementById('easterEggEmojiParticles');
    if (container) {
        container.remove();
    }
}

/**
 * パーティクル効果の停止
 */
function stopParticleEffect() {
    const container = document.getElementById('easterEggParticles');
    if (container) {
        container.remove();
    }
}

/**
 * 感謝モーダル関連の関数は削除（使用しない）
 * 感謝系は通常相談処理に流し、アニメーションのみ実行する
 */

/**
 * 画面回転
 */
function triggerRotation() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    container.style.transition = 'transform 1s ease-in-out';
    container.style.transform = 'rotate(360deg)';
    
    setTimeout(() => {
        container.style.transform = 'rotate(0deg)';
        setTimeout(() => {
            container.style.transition = '';
            container.style.transform = '';
            finishEasterEgg();
        }, 1000);
    }, 1000);
}

/**
 * 画面傾き
 */
function triggerSkew() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    container.style.transition = 'transform 1s ease-in-out';
    container.style.transform = 'skew(5deg, 0deg)';
    
    setTimeout(() => {
        container.style.transform = 'skew(0deg, 0deg)';
        setTimeout(() => {
            container.style.transition = '';
            container.style.transform = '';
            finishEasterEgg();
        }, 1000);
    }, 1000);
}

/**
 * 画面揺れ
 */
function triggerShake() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    // CSSアニメーションを追加
    if (!document.getElementById('easterEggShakeStyles')) {
        const style = document.createElement('style');
        style.id = 'easterEggShakeStyles';
        style.textContent = `
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-10px); }
                20%, 40%, 60%, 80% { transform: translateX(10px); }
            }
        `;
        document.head.appendChild(style);
    }
    
    container.style.animation = 'shake 0.5s ease-in-out 3';
    
    setTimeout(() => {
        container.style.animation = '';
        finishEasterEgg();
    }, 1500);
}

/**
 * 画面拡大・縮小
 */
function triggerZoom() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    container.style.transition = 'transform 0.8s ease-in-out';
    container.style.transform = 'scale(1.2)';
    
    setTimeout(() => {
        container.style.transform = 'scale(0.9)';
        setTimeout(() => {
            container.style.transform = 'scale(1)';
            setTimeout(() => {
                container.style.transition = '';
                container.style.transform = '';
                finishEasterEgg();
            }, 400);
        }, 400);
    }, 400);
}

/**
 * 画面反転
 */
function triggerFlip() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    container.style.transition = 'transform 0.6s ease-in-out';
    container.style.transform = 'scaleX(-1)';
    
    setTimeout(() => {
        container.style.transform = 'scaleX(1)';
        setTimeout(() => {
            container.style.transition = '';
            container.style.transform = '';
            finishEasterEgg();
        }, 600);
    }, 600);
}

/**
 * 画面バウンス
 */
function triggerBounce() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    // CSSアニメーションを追加
    if (!document.getElementById('easterEggBounceStyles')) {
        const style = document.createElement('style');
        style.id = 'easterEggBounceStyles';
        style.textContent = `
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                25% { transform: translateY(-30px); }
                50% { transform: translateY(0); }
                75% { transform: translateY(-15px); }
            }
        `;
        document.head.appendChild(style);
    }
    
    container.style.animation = 'bounce 0.8s ease-in-out 3';
    
    setTimeout(() => {
        container.style.animation = '';
        finishEasterEgg();
    }, 2400);
}

/**
 * 画面脈動
 */
function triggerPulse() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    // CSSアニメーションを追加
    if (!document.getElementById('easterEggPulseStyles')) {
        const style = document.createElement('style');
        style.id = 'easterEggPulseStyles';
        style.textContent = `
            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.9; }
            }
        `;
        document.head.appendChild(style);
    }
    
    container.style.animation = 'pulse 0.6s ease-in-out 4';
    
    setTimeout(() => {
        container.style.animation = '';
        finishEasterEgg();
    }, 2400);
}

/**
 * 画面光る効果
 */
function triggerGlow() {
    const container = document.querySelector('.chat-container');
    if (!container) return;
    
    // CSSアニメーションを追加
    if (!document.getElementById('easterEggGlowStyles')) {
        const style = document.createElement('style');
        style.id = 'easterEggGlowStyles';
        style.textContent = `
            @keyframes glow {
                0%, 100% { 
                    filter: drop-shadow(0 0 0px rgba(255, 255, 255, 0));
                    box-shadow: 0 0 0px rgba(255, 255, 255, 0);
                }
                50% { 
                    filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.8));
                    box-shadow: 0 0 30px rgba(255, 255, 255, 0.6);
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    container.style.animation = 'glow 0.8s ease-in-out 3';
    
    setTimeout(() => {
        container.style.animation = '';
        container.style.filter = '';
        container.style.boxShadow = '';
        finishEasterEgg();
    }, 2400);
}

/**
 * 花火アニメーション
 */
function triggerFireworks() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const canvas = document.createElement('canvas');
    canvas.id = 'fireworksCanvas';
    canvas.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9998;
    `;
    document.body.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const ps = eggParticleScale();
    const sparkR = Math.max(1.5, 3 * ps);
    
    const particles = [];
    const particleCount = window.innerWidth < 768 ? 30 : 50; // モバイルでは固定削減
    
    // 花火を生成
    for (let i = 0; i < particleCount; i++) {
        const x = Math.random() * canvas.width;
        const y = Math.random() * canvas.height * 0.5;
        const color = `hsl(${Math.random() * 360}, 100%, 50%)`;
        
        for (let j = 0; j < 20; j++) {
            particles.push({
                x,
                y,
                vx: (Math.random() - 0.5) * 10 * ps,
                vy: (Math.random() - 0.5) * 10 * ps,
                color,
                life: 1.0,
                decay: Math.random() * 0.02 + 0.01
            });
        }
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life -= p.decay;
            
            if (p.life > 0) {
                ctx.globalAlpha = p.life;
                ctx.fillStyle = p.color;
                ctx.beginPath();
                ctx.arc(p.x, p.y, sparkR, 0, Math.PI * 2);
                ctx.fill();
            } else {
                particles.splice(i, 1);
            }
        }
        
        if (particles.length > 0) {
            requestAnimationFrame(animate);
        } else {
            canvas.remove();
            finishEasterEgg();
        }
    }
    
    animate();
    
    // 2秒後に強制停止
    setTimeout(() => {
        canvas.remove();
        finishEasterEgg();
    }, 2000);
}

/**
 * 雪アニメーション（既存機能とは別）
 */
function triggerSnow() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const snowContainer = document.createElement('div');
    snowContainer.id = 'easterEggSnow';
    snowContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9998;
    `;
    document.body.appendChild(snowContainer);
    
    const snowflakes = ['❄', '❅', '❆', '❄', '❅', '❆', '❄', '❅'];
    const snowCount = window.innerWidth < 768 ? 50 : 80; // 数を大幅に増加
    const ps = eggParticleScale();
    const fallPad = eggPx(50);
    
    for (let i = 0; i < snowCount; i++) {
        const snowflake = document.createElement('div');
        snowflake.textContent = snowflakes[Math.floor(Math.random() * snowflakes.length)];
        const size = eggPx(20 + Math.random() * 30); // フォントサイズを大きく（20-50px 基準をビューポートで補正）
        const fallDuration = 4 + Math.random() * 3; // 落下時間を長く（4-7秒）
        const horizontalDrift = (Math.random() - 0.5) * 100 * ps; // 横方向の流れを増やす
        snowflake.style.cssText = `
            position: absolute;
            font-size: ${size}px;
            left: ${Math.random() * 100}%;
            top: ${-fallPad}px;
            animation: snowFall${i} ${fallDuration}s linear forwards;
            animation-delay: ${Math.random() * 2}s;
            opacity: ${0.85 + Math.random() * 0.15}; /* 透明度を上げる（0.85-1.0） */
            filter: drop-shadow(0 0 2px rgba(255, 255, 255, 0.8));
        `;
        snowContainer.appendChild(snowflake);
        
        // 各雪に個別のアニメーションを設定
        const style = document.createElement('style');
        style.id = `snowFallStyle${i}`;
        style.textContent = `
            @keyframes snowFall${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg);
                    opacity: ${0.85 + Math.random() * 0.15};
                }
                100% {
                    transform: translateY(calc(100vh + ${fallPad}px)) translateX(${horizontalDrift}px) rotate(720deg);
                    opacity: 0.3;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // 5秒後に停止
    setTimeout(() => {
        snowContainer.remove();
        // 個別のスタイルも削除
        for (let i = 0; i < snowCount; i++) {
            const style = document.getElementById(`snowFallStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, 5000);
}

/**
 * 雨アニメーション
 */
function triggerRain() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const rainContainer = document.createElement('div');
    rainContainer.id = 'easterEggRain';
    rainContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9998;
    `;
    document.body.appendChild(rainContainer);
    
    const rainCount = window.innerWidth < 768 ? 60 : 100; // 数を大幅に増加
    
    for (let i = 0; i < rainCount; i++) {
        const drop = document.createElement('div');
        const width = 2 + Math.random() * 2; // 太さを太く（2-4px）
        const height = 30 + Math.random() * 40; // 長さを長く（30-70px）
        const speed = 0.3 + Math.random() * 0.4; // 速度を調整（0.3-0.7秒）
        const opacity = 0.7 + Math.random() * 0.3; // 透明度を上げる（0.7-1.0）
        drop.style.cssText = `
            position: absolute;
            width: ${width}px;
            height: ${height}px;
            background: linear-gradient(to bottom, rgba(100, 150, 255, ${opacity}), rgba(100, 150, 255, ${opacity * 0.5}));
            left: ${Math.random() * 100}%;
            top: -${height}px;
            animation: rainFall${i} ${speed}s linear infinite;
            animation-delay: ${Math.random() * 1}s;
            box-shadow: 0 0 3px rgba(100, 150, 255, 0.5);
        `;
        rainContainer.appendChild(drop);
        
        // 各雨に個別のアニメーションを設定
        const style = document.createElement('style');
        style.id = `rainFallStyle${i}`;
        style.textContent = `
            @keyframes rainFall${i} {
                0% {
                    transform: translateY(0);
                    opacity: ${opacity};
                }
                100% {
                    transform: translateY(calc(100vh + ${height}px));
                    opacity: 0.2;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // 4秒後に停止
    setTimeout(() => {
        rainContainer.remove();
        // 個別のスタイルも削除
        for (let i = 0; i < rainCount; i++) {
            const style = document.getElementById(`rainFallStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, 4000);
}

/**
 * 「謹賀新年」縦書きアニメーション
 * 大人っぽくカッコいいデザインで表示
 */
function showKeigaShinnen() {
    // 既存の要素があれば削除
    const existing = document.getElementById('keigaShinnenText');
    if (existing) existing.remove();
    
    const textContainer = document.createElement('div');
    textContainer.id = 'keigaShinnenText';
    textContainer.className = 'keiga-shinnen-text';
    
    // 縦書きで4文字を表示
    const characters = ['謹', '賀', '新', '年'];
    characters.forEach((char, index) => {
        const charSpan = document.createElement('span');
        charSpan.className = 'keiga-char';
        charSpan.textContent = char;
        charSpan.style.animationDelay = `${index * 0.1}s`;
        textContainer.appendChild(charSpan);
    });
    
    document.body.appendChild(textContainer);
    
    // アニメーション完了後にwill-changeを削除してパフォーマンスを最適化
    setTimeout(() => {
        const chars = textContainer.querySelectorAll('.keiga-char');
        chars.forEach(char => {
            char.style.willChange = 'auto';
        });
    }, 2000); // アニメーション完了後
    
    // 5秒後に自動削除
    setTimeout(() => {
        const element = document.getElementById('keigaShinnenText');
        if (element) {
            element.style.animation = 'keigaShinnenFadeOut 0.8s ease-out forwards';
            setTimeout(() => element.remove(), 800);
        }
    }, 5000);
}

/**
 * 新年アニメーション（花火とパーティクル効果）
 */
function triggerNewYear() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    // 花火アニメーションを実行
    triggerFireworks();
    
    // 「謹賀新年」アニメーションを表示
    showKeigaShinnen();
    
    // 新年用のパーティクル効果を追加
    const particleContainer = document.createElement('div');
    particleContainer.id = 'easterEggNewYearParticles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(particleContainer);
    
    const newYearParticles = ['🎊', '🎉', '🎈', '✨', '⭐', '🌟', '💫', '🎁'];
    const particleCount = window.innerWidth < 768 ? 40 : 60;
    const ps = eggParticleScale();
    const fallPad = eggPx(50);
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.textContent = newYearParticles[Math.floor(Math.random() * newYearParticles.length)];
        const fontSize = eggPx(25 + Math.random() * 30);
        const duration = 3 + Math.random() * 2;
        const horizontalDrift = (Math.random() - 0.5) * 150 * ps;
        
        particle.style.cssText = `
            position: absolute;
            font-size: ${fontSize}px;
            left: ${Math.random() * 100}%;
            top: ${-fallPad}px;
            animation: newYearParticleFall${i} ${duration}s linear forwards;
            animation-delay: ${Math.random() * 2}s;
            opacity: 0.9;
            filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.6));
        `;
        particleContainer.appendChild(particle);
        
        // 各パーティクルに個別のアニメーションを設定
        const style = document.createElement('style');
        style.id = `newYearParticleStyle${i}`;
        style.textContent = `
            @keyframes newYearParticleFall${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg) scale(0.8);
                    opacity: 0.9;
                }
                50% {
                    transform: translateY(50vh) translateX(${horizontalDrift * 0.5}px) rotate(180deg) scale(1.2);
                    opacity: 0.95;
                }
                100% {
                    transform: translateY(calc(100vh + ${fallPad}px)) translateX(${horizontalDrift}px) rotate(360deg) scale(0.6);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // 5秒後に自動停止
    setTimeout(() => {
        particleContainer.remove();
        // 個別のスタイルも削除
        for (let i = 0; i < particleCount; i++) {
            const style = document.getElementById(`newYearParticleStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, 5000);
}

/**
 * 誕生日アニメーション（ケーキと風船のパーティクル効果）
 */
function triggerBirthday() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const birthdayContainer = document.createElement('div');
    birthdayContainer.id = 'easterEggBirthdayParticles';
    birthdayContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(birthdayContainer);
    
    const birthdayParticles = ['🎂', '🎁', '🎈', '🎉', '🎊', '✨', '⭐', '🌟', '💫', '🎀'];
    const particleCount = window.innerWidth < 768 ? 50 : 70;
    const ps = eggParticleScale();
    const edgePad = eggPx(50);
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.textContent = birthdayParticles[Math.floor(Math.random() * birthdayParticles.length)];
        const fontSize = eggPx(30 + Math.random() * 35);
        const duration = 4 + Math.random() * 2;
        const horizontalDrift = (Math.random() - 0.5) * 200 * ps;
        const startDelay = Math.random() * 2;
        
        // 風船は上に、ケーキやプレゼントは下に落ちる
        const isBalloon = /[🎈]/.test(particle.textContent);
        const startY = isBalloon ? `calc(100vh + ${edgePad}px)` : `${-edgePad}px`;
        const endY = isBalloon ? `${-edgePad}px` : `calc(100vh + ${edgePad}px)`;
        const rotation = isBalloon ? -360 : 360;
        
        particle.style.cssText = `
            position: absolute;
            font-size: ${fontSize}px;
            left: ${Math.random() * 100}%;
            top: ${startY};
            animation: birthdayParticleMove${i} ${duration}s linear forwards;
            animation-delay: ${startDelay}s;
            opacity: 0.9;
            filter: drop-shadow(0 0 5px rgba(255, 255, 255, 0.7));
        `;
        birthdayContainer.appendChild(particle);
        
        // 各パーティクルに個別のアニメーションを設定
        const style = document.createElement('style');
        style.id = `birthdayParticleStyle${i}`;
        style.textContent = `
            @keyframes birthdayParticleMove${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg) scale(0.8);
                    opacity: 0.9;
                }
                50% {
                    transform: translateY(${isBalloon ? '-50vh' : '50vh'}) translateX(${horizontalDrift * 0.5}px) rotate(${rotation * 0.5}deg) scale(1.2);
                    opacity: 1;
                }
                100% {
                    transform: translateY(${endY}) translateX(${horizontalDrift}px) rotate(${rotation}deg) scale(0.6);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // 6秒後に自動停止
    setTimeout(() => {
        birthdayContainer.remove();
        // 個別のスタイルも削除
        for (let i = 0; i < particleCount; i++) {
            const style = document.getElementById(`birthdayParticleStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, 6000);
}

/**
 * クリスマスアニメーション（雪とクリスマスパーティクル）
 */
function triggerChristmas() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    // 雪アニメーションを実行
    triggerSnow();
    
    // クリスマス用のパーティクル効果を追加
    const particleContainer = document.createElement('div');
    particleContainer.id = 'easterEggChristmasParticles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(particleContainer);
    
    const christmasParticles = ['🎄', '🎅', '🎁', '🎄', '⭐', '🌟', '✨', '💫', '🔔', '❄️'];
    const particleCount = window.innerWidth < 768 ? 40 : 60;
    const ps = eggParticleScale();
    const fallPad = eggPx(50);
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.textContent = christmasParticles[Math.floor(Math.random() * christmasParticles.length)];
        const fontSize = eggPx(25 + Math.random() * 30);
        const duration = 3 + Math.random() * 2;
        const horizontalDrift = (Math.random() - 0.5) * 150 * ps;
        
        particle.style.cssText = `
            position: absolute;
            font-size: ${fontSize}px;
            left: ${Math.random() * 100}%;
            top: ${-fallPad}px;
            animation: christmasParticleFall${i} ${duration}s linear forwards;
            animation-delay: ${Math.random() * 2}s;
            opacity: 0.9;
            filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.6));
        `;
        particleContainer.appendChild(particle);
        
        const style = document.createElement('style');
        style.id = `christmasParticleStyle${i}`;
        style.textContent = `
            @keyframes christmasParticleFall${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg) scale(0.8);
                    opacity: 0.9;
                }
                50% {
                    transform: translateY(50vh) translateX(${horizontalDrift * 0.5}px) rotate(180deg) scale(1.2);
                    opacity: 0.95;
                }
                100% {
                    transform: translateY(calc(100vh + ${fallPad}px)) translateX(${horizontalDrift}px) rotate(360deg) scale(0.6);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        particleContainer.remove();
        for (let i = 0; i < particleCount; i++) {
            const style = document.getElementById(`christmasParticleStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, 5000);
}

/**
 * ハロウィンアニメーション（ハロウィンパーティクル）
 */
function triggerHalloween() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const halloweenContainer = document.createElement('div');
    halloweenContainer.id = 'easterEggHalloweenParticles';
    halloweenContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(halloweenContainer);
    
    const halloweenParticles = ['🎃', '👻', '🦇', '🕷️', '🕸️', '💀', '☠️', '🧙', '🧛', '🧟'];
    const particleCount = window.innerWidth < 768 ? 50 : 70;
    const ps = eggParticleScale();
    const fallPad = eggPx(50);
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.textContent = halloweenParticles[Math.floor(Math.random() * halloweenParticles.length)];
        const fontSize = eggPx(30 + Math.random() * 35);
        const duration = 4 + Math.random() * 2;
        const horizontalDrift = (Math.random() - 0.5) * 200 * ps;
        const startDelay = Math.random() * 2;
        
        particle.style.cssText = `
            position: absolute;
            font-size: ${fontSize}px;
            left: ${Math.random() * 100}%;
            top: ${-fallPad}px;
            animation: halloweenParticleMove${i} ${duration}s linear forwards;
            animation-delay: ${startDelay}s;
            opacity: 0.9;
            filter: drop-shadow(0 0 5px rgba(255, 165, 0, 0.7));
        `;
        halloweenContainer.appendChild(particle);
        
        const style = document.createElement('style');
        style.id = `halloweenParticleStyle${i}`;
        style.textContent = `
            @keyframes halloweenParticleMove${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg) scale(0.8);
                    opacity: 0.9;
                }
                50% {
                    transform: translateY(50vh) translateX(${horizontalDrift * 0.5}px) rotate(180deg) scale(1.2);
                    opacity: 1;
                }
                100% {
                    transform: translateY(calc(100vh + ${fallPad}px)) translateX(${horizontalDrift}px) rotate(360deg) scale(0.6);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        halloweenContainer.remove();
        for (let i = 0; i < particleCount; i++) {
            const style = document.getElementById(`halloweenParticleStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, 6000);
}

/**
 * 汎用イベントパーティクル効果（バレンタイン、ホワイトデー、七夕、お盆など）
 * @param {string} eventId - イベントID
 * @param {string[]} particles - 使用する絵文字の配列
 * @param {number} duration - アニメーション時間（秒）
 */
function triggerGenericEvent(eventId, particles, duration = 5000) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const eventContainer = document.createElement('div');
    eventContainer.id = `easterEgg${eventId}Particles`;
    eventContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(eventContainer);
    
    const particleCount = window.innerWidth < 768 ? 40 : 60;
    const ps = eggParticleScale();
    const fallPad = eggPx(50);
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.textContent = particles[Math.floor(Math.random() * particles.length)];
        const fontSize = eggPx(25 + Math.random() * 30);
        const animDuration = 3 + Math.random() * 2;
        const horizontalDrift = (Math.random() - 0.5) * 150 * ps;
        
        particle.style.cssText = `
            position: absolute;
            font-size: ${fontSize}px;
            left: ${Math.random() * 100}%;
            top: ${-fallPad}px;
            animation: ${eventId}ParticleFall${i} ${animDuration}s linear forwards;
            animation-delay: ${Math.random() * 2}s;
            opacity: 0.9;
            filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.6));
        `;
        eventContainer.appendChild(particle);
        
        const style = document.createElement('style');
        style.id = `${eventId}ParticleStyle${i}`;
        style.textContent = `
            @keyframes ${eventId}ParticleFall${i} {
                0% {
                    transform: translateY(0) translateX(0) rotate(0deg) scale(0.8);
                    opacity: 0.9;
                }
                50% {
                    transform: translateY(50vh) translateX(${horizontalDrift * 0.5}px) rotate(180deg) scale(1.2);
                    opacity: 0.95;
                }
                100% {
                    transform: translateY(calc(100vh + ${fallPad}px)) translateX(${horizontalDrift}px) rotate(360deg) scale(0.6);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        eventContainer.remove();
        for (let i = 0; i < particleCount; i++) {
            const style = document.getElementById(`${eventId}ParticleStyle${i}`);
            if (style) style.remove();
        }
        finishEasterEgg();
    }, duration);
}

/**
 * バレンタインアニメーション
 */
function triggerValentine() {
    triggerGenericEvent('Valentine', ['💝', '💕', '💖', '💗', '💓', '💞', '💟', '❤️', '💘', '🌹'], 5000);
}

/**
 * ホワイトデーアニメーション
 */
function triggerWhiteDay() {
    triggerGenericEvent('WhiteDay', ['🤍', '💝', '🎁', '💕', '💖', '💗', '💓', '💞', '💟', '❤️'], 5000);
}

/**
 * 七夕アニメーション
 */
function triggerTanabata() {
    triggerGenericEvent('Tanabata', ['🎋', '⭐', '🌟', '✨', '💫', '🌠', '⭐', '🌟', '✨', '💫'], 5000);
}

/**
 * お盆アニメーション
 */
function triggerObon() {
    triggerGenericEvent('Obon', ['🕯️', '🏮', '🎐', '✨', '💫', '🕯️', '🏮', '🎐', '✨', '💫'], 5000);
}

/**
 * こどもの日アニメーション
 */
function triggerChildrensDay() {
    triggerGenericEvent('ChildrensDay', ['🎏', '🎎', '🎌', '🎊', '🎉', '🎈', '🎁', '✨', '⭐', '🌟'], 5000);
}

/**
 * 母の日アニメーション
 */
function triggerMothersDay() {
    triggerGenericEvent('MothersDay', ['💐', '🌷', '🌹', '🌺', '🌸', '🌻', '🌼', '💕', '💖', '💗'], 5000);
}

/**
 * 父の日アニメーション
 */
function triggerFathersDay() {
    triggerGenericEvent('FathersDay', ['👔', '🎁', '🍺', '🍻', '🎉', '🎊', '💝', '💕', '💖', '💗'], 5000);
}

/**
 * 敬老の日アニメーション
 */
function triggerRespectForTheAgedDay() {
    triggerGenericEvent('RespectForTheAgedDay', ['👴', '👵', '🌻', '🌷', '🌹', '💐', '💝', '💕', '💖', '💗'], 5000);
}

/**
 * 大晦日アニメーション
 */
function triggerNewYearsEve() {
    // 「謹賀新年」アニメーションを表示
    showKeigaShinnen();
    
    triggerGenericEvent('NewYearsEve', ['🎊', '🎉', '🎈', '✨', '⭐', '🌟', '💫', '🎁', '🎊', '🎉'], 5000);
}

/**
 * モーダルの閉じ方実装
 * @param {string} modalId - モーダルID
 */
function setupModalCloseHandlers(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    // Escapeキー（グローバルイベントリスナーとして一度だけ追加）
    if (!window.easterEggEscapeHandler) {
        window.easterEggEscapeHandler = (e) => {
            if (e.key === 'Escape') {
                // 表示中のモーダルを検出
                const openModal = document.querySelector('.modal[style*="display: block"]') || 
                                 document.querySelector('.modal:not([style*="display: none"])');
                if (openModal) {
                    const modalId = openModal.id;
                    if (modalId === 'snakeModal') {
                        if (window.closeSnakeModal) window.closeSnakeModal();
                    } else {
                        openModal.style.display = 'none';
                        if (openModal.hasAttribute('aria-hidden')) {
                            openModal.setAttribute('aria-hidden', 'true');
                        }
                        finishEasterEgg();
                    }
                }
            }
        };
        document.addEventListener('keydown', window.easterEggEscapeHandler);
    }
    
    // モーダル外クリック
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            if (modalId === 'snakeModal') {
                if (window.closeSnakeModal) window.closeSnakeModal();
            } else {
                modal.style.display = 'none';
                if (modal.hasAttribute('aria-hidden')) {
                    modal.setAttribute('aria-hidden', 'true');
                }
                finishEasterEgg();
            }
        }
    });
}

/**
 * スネークゲームの起動（動的インポート）
 */
async function triggerSnakeGame() {
    try {
        // 動的インポートのパスを絶対パスに変更（Flaskの静的ファイルパス）
        const { initSnakeGame } = await import('/static/js/games/snake.js');
        initSnakeGame();
    } catch (err) {
        console.error('[EasterEgg] Failed to load Snake Game:', err);
        logEasterEggError(err, 'triggerSnakeGame', {});
        finishEasterEgg();
    }
}


// グローバルに公開
if (typeof window !== 'undefined') {
    window.checkEasterEggs = checkEasterEggs;
    window.finishEasterEgg = finishEasterEgg;
    window.triggerThanksAnimation = triggerThanksAnimation; // 感謝系アニメーション用
}

