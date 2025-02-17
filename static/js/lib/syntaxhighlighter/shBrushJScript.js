/**
 * SyntaxHighlighter
 * http://alexgorbatchev.com/SyntaxHighlighter
 *
 * SyntaxHighlighter is donationware. If you are using it, please donate.
 * http://alexgorbatchev.com/SyntaxHighlighter/donate.html
 *
 * @version
 * 3.0.90 (Thu, 17 Nov 2016 14:18:05 GMT)
 *
 * @copyright
 * Copyright (C) 2004-2013 Alex Gorbatchev.
 *
 * @license
 * Dual licensed under the MIT and GPL licenses.
 */
(function () {
  // CommonJS
  SyntaxHighlighter =
    SyntaxHighlighter ||
    (typeof require !== 'undefined'
      ? require('shCore').SyntaxHighlighter
      : null);

  function Brush() {
    var keywords =
      'break case catch class continue ' +
      'default delete do else enum export extends false  ' +
      'for function if implements import in instanceof ' +
      'interface let new null package private protected ' +
      'static return super switch ' +
      'this throw true try typeof var while with yield';

    var r = SyntaxHighlighter.regexLib;

    this.regexList = [
      { regex: r.multiLineDoubleQuotedString, css: 'string' }, // double quoted strings
      { regex: r.multiLineSingleQuotedString, css: 'string' }, // single quoted strings
      { regex: r.singleLineCComments, css: 'comments' }, // one line comments
      { regex: r.multiLineCComments, css: 'comments' }, // multiline comments
      { regex: /\s*#.*/gm, css: 'preprocessor' }, // preprocessor tags like #region and #endregion
      { regex: new RegExp(this.getKeywords(keywords), 'gm'), css: 'keyword' }, // keywords
    ];

    this.forHtmlScript(r.scriptScriptTags);
  }

  Brush.prototype = new SyntaxHighlighter.Highlighter();
  Brush.aliases = ['js', 'jscript', 'javascript', 'json'];

  SyntaxHighlighter.brushes.JScript = Brush;

  // CommonJS
  typeof exports != 'undefined' ? (exports.Brush = Brush) : null;
})();
