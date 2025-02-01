---
created: 2024-11-15T14:17
updated: 2024-11-15T14:20
---
## With unicode-math

The `unicode-math` package defines all the following math alphabets:

`\mathup` Upright serif

`\mathbfup` Bold upright serif

`\mathit` Italic serif

`\mathbfit` Bold italic serif

`\mathsfup` Upright sans-serif

`\mathsfit` Italic sans-serif

`\mathbfsfup` Bold upright sans-serif

`\mathbfsfit`¹ Bold italic sans-serif

`\mathtt` Typewriter

`\mathbb` Blackboard bold

`\mathbbit` Blackboard bold italic

`\mathscr` Script

`\mathbfscr` Bold script²

`\mathcal` Calligraphic

`\mathbfcal` Bold calligraphic²

`\mathfrak` Fraktur

`\mathbffrak` Bold Fraktur²

It is also possible to `\setoperatorfont` to change the font of operators such as `\sin` and `\cos`.

The package supports uppercase and lowercase, Latin and Greek, and numerals for all the alphabets that Unicode does.

The package declares synonyms for backward-compatibility, such as `\mathrm` for `\mathup`. It also defines `\mathnormal`, whose behavior can be changed with the `math-style=` package option, and `\symliteral`, to display symbols exactly as they are typed in.

Each of these also has a corresponding command such as `\symup`, `\symit` and so on, and these can be set to a different math alphabet from the corresponding text-mode math alphabet. The `\sym` variants are intended for strings of individual math symbols, and the `\math` variants for words to be rendered as text (and for backwards-compatibility).

The `range=` option of `\setmathfont` provides a very flexible way to load each of these math alphabets, or subsets of them, or even individual symbols, from any Unicode font.

By default, `unicode-math` loads both `\mathcal` and `\mathscr` as the same alphabet, but you can nevertheless load a different font for both (although it would be unusual to use both `\mathcal` and `\mathscr` within the same document). The `\mathrm` and `\symup` alphabets are also both set to the text font, but either can be changed: `\mathrm` is for words such as tan or PROFIT = REVENUE - COSTS, and `\symup` is for upright mathematical symbols such as 2πi. You can change the `\mathrm` font with `\setmathrm`, and the math bold, italic and bold italic fonts by passing said command the `BoldFont =` option. This will not change fonts such as `\symit`.

Here is an example where `\mathrm` and `\symup` are set to different alpabets. In this document, the text font and therefore `\mathrm` are a Palatino clone (TeX Gyre Pagella) and the math font is another Palatino clone (Asana Math), while `\symup` is set to a different font (Neo Euler, a clone of AMS Euler). This sets the Euler equation in ISO style, with the symbols for constants upright and the symbols for variables italic. Notice the contrast between the upright i symbol for the imaginary unit, the letter i in sin, and the italic variable _x_. This example also doesn’t change the numerals (despite their being part of the upright serif math alphabet), so that `$1$` still looks the same as `1`.

```latex
\documentclass[varwidth, preview]{standalone} \usepackage{mathtools} \usepackage[math-style=ISO]{unicode-math} \setmainfont{TeX Gyre Pagella} \defaultfontfeatures{Scale=MatchLowercase} \setmathfont{Asana Math} \setmathfont[range={up/{Latin,latin,Greek,greek}, bfup/{Latin,latin,Greek,greek}}, script-features={}, sscript-features={} ]{Neo Euler} \newcommand\upe{\symup{e}} \newcommand\upi{\symup{i}} \begin{document} \begin{align*} \upe^{\upi x} &= \cos{x} + \upi \sin{x} \\ \upe^{\upi \uppi} + 1 &= 0 \end{align*} \end{document}
```

[![Different \mathrm and \symup](https://i.sstatic.net/Pds3z.png)](https://i.sstatic.net/Pds3z.png)

The package also supports bold math style and the commands `\mathbold`, write `\mathversion{bold}` and `\boldsymbol` from `amsmath`, so it would let you call `\boldsymbol\mathbb{C}`. If you load a Unicode math font that has a bold version, `unicode-math` will load it for you. As of July 2019, that applies to XITS Math, Libertinus Math and Minion Math. You can also load one manually with a command such as `\setmathfont[version=bold]{Minion Math Semibold}`.

You do not need any other packages to use any of these alphabets, other than the packages for your OTF fonts.

## With NFSS

Any Unicode math font will give you more alphabets than any combination of legacy packages. It isn’t even possible to define that many alphabets in NFSS.

As egreg mentioned, the LaTeX kernel defines `\mathrm`, `\mathnormal`, `\mathit`, `\mathbf`, `\mathsf`, `\mathtt`, and `\mathcal`.

A large number of packages define more math alphabets, but two are especially convenient for setting up properly-scaled math alphabets with a comprehensive selection of fonts. The `isomath` package defines the alphabets `\mathbfit`, `\mathsfit`, and `\mathsfbfit`,¹ loads Greek letters for some alphabets that didn’t have them, and allows you to choose between several different fonts. The `mathalpha` (formerly `mathalfa`) package allows you to set `\mathcal`, as well as the new alphabets `\mathbb`, `\mathfrak`, `\mathscr`, `\mathbcal`, `\mathbbb`, `\mathbfrak` and `\mathbscr`.² You may also use the `\bm` and `\hm` commands from the `bm` package to get bold and heavy math symbols, respectively.

Traditionally, you would get `\mathfrak` and `\mathbb` from `amsfonts`, or the AMS also provided alternatives in the `eucal` and `eufrak` packages. The `\mathscr` command started as an alternative script alphabet for “Lagrangian density, Hamiltonian density, or the measure in the path integral” in physics papers. It became a way to load an alternative script alphabet without overriding `\mathcal`, and most such alphabets could instead be loaded as `\mathcal`. For example, `euscript` or `eucal` load Euler Script as `\mathscr` or `\mathcal`, and `mathrsfs` or `calrsfs` load Ralph Smith Formal Script as `\mathscr` or `\mathcal`. It would be unusual to use both alphabets in the same document, but if you do need to, I recommend `rfsfo` as one that’s distinct from `\mathcal`, appropriate for the original purpose of `\mathscr`, and not too slanted.

Many font packages also add math alphabets, including `lmodern`, `stix`, `stix2`, `newtxmath`, `newpxmath` and `ccfonts`. These usually use the same names as `amsfonts` and `unicode-math`. [Table 307 of the Comprehensive LaTeX Symbol List](http://tug.ctan.org/info/symbols/comprehensive/symbols-a4.pdf#section*.311) shows math alphabets defined by other legacy packages.

¹ The math bold italic sans-serif command is `\mathbfsfit` in `unicode-math` but `\mathsfbfit` in `isomath`.

² The `\mathbfcal`, `\mathbffrak`, and `\mathbfscr` alphabets previously had different names in `mathalpha`, and there is a compatibility option to use their old names. There is no bold double-struck alphabet in `unicode-math`, although you could define a bold math style and use its `\symbb`, and no italic blackboard bold in `mathalpha`.

![[Pasted image 20241115141836.png]]
![[Pasted image 20241115141848.png]]

[The Comprehensive LaTeX Symbol List](https://ctan.math.utah.edu/ctan/tex-archive/info/symbols/comprehensive/symbols-a4.pdf#page=123)

[LaTeX Math Symbols Cheat Sheet - Kapeli](https://kapeli.com/cheat_sheets/LaTeX_Math_Symbols.docset/Contents/Resources/Documents/index)