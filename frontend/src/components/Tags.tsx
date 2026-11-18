import { useMemo, useState } from "react";

type TagsProps = {
  value: string[];
  setValue: (tags: string[]) => void;
  suggestions: string[];
};

export default function Tags({
  value,
  setValue,
  suggestions,
}: TagsProps) {
  const safeValue = Array.isArray(value) ? value : [];
  const safeSuggestions = Array.isArray(suggestions) ? suggestions : [];

  const [inputText, setInputText] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const normalizeTag = (tag: string) => tag.trim().toLocaleLowerCase();

  const tagAlreadyExists = (tag: string) => {
    const normalizedTag = normalizeTag(tag);
    return safeValue.some(
      (existingTag) => normalizeTag(existingTag) === normalizedTag,
    );
  };

  const matches = useMemo(() => {
    const searchText = inputText.trim().toLocaleLowerCase();

    if (!searchText) {
      return [];
    }

    return safeSuggestions
      .filter((suggestion) => {
        const normalizedSuggestion = normalizeTag(suggestion);
        return (
          normalizedSuggestion.includes(searchText) &&
          !safeValue.some(
            (existingTag) =>
              normalizeTag(existingTag) === normalizedSuggestion,
          )
        );
      })
      .slice(0, 8);
  }, [inputText, safeSuggestions, safeValue]);

  const addTag = (tag: string) => {
    const cleanedTag = tag.trim();

    if (!cleanedTag) {
      return;
    }

    if (!tagAlreadyExists(cleanedTag)) {
      setValue([...safeValue, cleanedTag]);
    }

    setInputText("");
    setHighlightedIndex(0);
  };

  const removeTag = (tagToRemove: string) => {
    const normalizedTagToRemove = normalizeTag(tagToRemove);
    setValue(
      safeValue.filter(
        (existingTag) =>
          normalizeTag(existingTag) !== normalizedTagToRemove,
      ),
    );
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (event.key === "ArrowDown" && matches.length > 0) {
      event.preventDefault();
      setHighlightedIndex((currentIndex) =>
        (currentIndex + 1) % matches.length,
      );
      return;
    }

    if (event.key === "ArrowUp" && matches.length > 0) {
      event.preventDefault();
      setHighlightedIndex((currentIndex) =>
        (currentIndex - 1 + matches.length) % matches.length,
      );
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      addTag(matches.length > 0 ? matches[highlightedIndex] : inputText);
    }

    if (event.key === "Escape") {
      setInputText("");
      setHighlightedIndex(0);
    }
  };

  return (
    <div className="tagbox">
      <div className="tagrow">
        {safeValue.map((tag) => (
          <span key={normalizeTag(tag)}>
            {tag}
            <button
              type="button"
              aria-label={`Remove ${tag}`}
              onClick={() => removeTag(tag)}
            >
              ×
            </button>
          </span>
        ))}

        <input
          value={inputText}
          placeholder="Type tag + Enter"
          onChange={(event) => {
            setInputText(event.target.value);
            setHighlightedIndex(0);
          }}
          onKeyDown={handleKeyDown}
        />
      </div>

      {inputText.trim() && matches.length > 0 ? (
        <div className="tagmenu">
          {matches.map((suggestion, index) => (
            <button
              key={suggestion}
              type="button"
              className={index === highlightedIndex ? "selected" : ""}
              onMouseDown={(event) => {
                event.preventDefault();
                addTag(suggestion);
              }}
            >
              {suggestion}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
