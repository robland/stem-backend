import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Button, ChoiceGroup, Field, Input, ProgressBar } from "./components";

describe("Button", () => {
  it("est désactivé et occupé pendant le chargement", () => {
    render(<Button loading>Valider</Button>);
    const button = screen.getByRole("button", { name: "Valider" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("asChild : rend l'enfant (lien) avec le style du bouton", () => {
    render(
      <Button asChild variant="secondary">
        <a href="/scanner">Scanner</a>
      </Button>,
    );
    expect(screen.getByRole("link", { name: "Scanner" })).toHaveClass("rounded-lg");
  });
});

describe("Field", () => {
  it("relie libellé, aide et erreur au contrôle", () => {
    render(
      <Field label="Téléphone" hint="Ex. 06 123 45 67" error="Numéro invalide">
        {({ id, describedBy, invalid }) => <Input id={id} aria-describedby={describedBy} aria-invalid={invalid} />}
      </Field>,
    );
    const input = screen.getByLabelText("Téléphone");
    expect(input).toHaveAccessibleDescription("Ex. 06 123 45 67 Numéro invalide");
    expect(input).toHaveAttribute("aria-invalid", "true");
  });
});

describe("ChoiceGroup", () => {
  it("choix unique au clavier et à la souris", async () => {
    function Levels() {
      const [value, setValue] = useState<"3e" | "Tle" | null>(null);
      return (
        <ChoiceGroup
          legend="Ta classe"
          value={value}
          onChange={setValue}
          options={[
            { value: "3e", label: "3e" },
            { value: "Tle", label: "Terminale" },
          ]}
        />
      );
    }
    render(<Levels />);
    await userEvent.click(screen.getByLabelText("Terminale"));
    expect(screen.getByLabelText("Terminale")).toBeChecked();
    expect(screen.getByLabelText("3e")).not.toBeChecked();
  });

  it("choix multiple", async () => {
    function Subjects() {
      const [value, setValue] = useState<("maths" | "pc")[]>(["maths"]);
      return (
        <ChoiceGroup
          multiple
          legend="Matières"
          value={value}
          onChange={setValue}
          options={[
            { value: "maths", label: "Maths" },
            { value: "pc", label: "Physique-Chimie" },
          ]}
        />
      );
    }
    render(<Subjects />);
    await userEvent.click(screen.getByLabelText("Physique-Chimie"));
    await userEvent.click(screen.getByLabelText("Maths"));
    expect(screen.getByLabelText("Physique-Chimie")).toBeChecked();
    expect(screen.getByLabelText("Maths")).not.toBeChecked();
  });
});

describe("ProgressBar", () => {
  it("borne la valeur entre 0 et 100", () => {
    render(<ProgressBar value={140} label="Progression" />);
    expect(screen.getByRole("progressbar", { name: "Progression" })).toHaveAttribute("aria-valuenow", "100");
  });
});
