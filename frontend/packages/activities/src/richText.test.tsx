import { render, screen, waitFor } from "@testing-library/react";
import { RichText } from "./RichText";
import { parseRichText } from "./richText";

describe("parseRichText", () => {
  it("sépare texte, formules en ligne et en bloc", () => {
    expect(parseRichText("Soit $f(x) = x^2$. On a $$f'(x) = 2x$$ fin")).toEqual([
      { kind: "text", value: "Soit " },
      { kind: "math", value: "f(x) = x^2", display: false },
      { kind: "text", value: ". On a " },
      { kind: "math", value: "f'(x) = 2x", display: true },
      { kind: "text", value: " fin" },
    ]);
  });

  it("rend \\ce{…} hors formule comme de la chimie, accolades imbriquées comprises", () => {
    expect(parseRichText("Équilibre \\ce{H2 + O2 -> H2O^{2+}}.")).toEqual([
      { kind: "text", value: "Équilibre " },
      { kind: "math", value: "\\ce{H2 + O2 -> H2O^{2+}}", display: false },
      { kind: "text", value: "." },
    ]);
  });

  it("garde un dollar échappé ou non fermé comme texte", () => {
    expect(parseRichText("Prix : 5 \\$ et $x")).toEqual([{ kind: "text", value: "Prix : 5 $ et $x" }]);
  });

  it("ne coupe pas une formule sur un \\$ intérieur", () => {
    expect(parseRichText("$a \\$ b$")).toEqual([{ kind: "math", value: "a \\$ b", display: false }]);
  });

  it("ignore une formule vide", () => {
    expect(parseRichText("$$")).toEqual([{ kind: "text", value: "$$" }]);
  });
});

describe("RichText", () => {
  it("n'interprète jamais de HTML", () => {
    const { container } = render(<RichText text={'<img src=x onerror="alert(1)"> texte'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x/)).toBeInTheDocument();
  });

  it("rend les formules avec KaTeX", async () => {
    const { container } = render(<RichText text="Soit $x^2$" />);
    await waitFor(() => expect(container.querySelector(".katex")).not.toBeNull());
  });

  it("rend la chimie avec mhchem", async () => {
    const { container } = render(<RichText text="\\ce{H2O}" />);
    await waitFor(() => expect(container.querySelector(".katex")).not.toBeNull());
    expect(container.querySelector(".katex-error")).toBeNull();
  });
});
