"use client";

import Uppy from "@uppy/core";
import { UppyContextProvider, useDropzone, useUppyState } from "@uppy/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ButtonHTMLAttributes, InputHTMLAttributes } from "react";
import { CloudUpload, FileText, Plus, X } from "lucide-react";

export type PdfFile = File;
type Props = {
  onFilesChange?: (files: PdfFile[]) => void;
  multiple?: boolean;
  label: string;
  compact?: boolean;
};

const PDF_TYPES = ["application/pdf", ".pdf"];
const PDF_ERROR = "Please upload PDF files only. Other file types aren’t accepted.";
const SINGLE_PDF_ERROR = "Only one PDF is allowed for your answer copy. Please select a single file.";
const formatSize = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

function isPdf(name: string, type?: string | null) {
  return name.toLowerCase().endsWith(".pdf") && (!type || type === "application/pdf");
}

export default function FileDropzone({
  onFilesChange,
  multiple = false,
  label,
  compact = false,
}: Props) {
  const [error, setError] = useState("");
  const instanceId = `upsc-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}`;
  const [uppy] = useState(
    () =>
      new Uppy({
        id: instanceId,
        autoProceed: false,
        restrictions: {
          allowedFileTypes: PDF_TYPES,
          maxNumberOfFiles: multiple ? null : 1,
        },
        onBeforeFileAdded: (file) => {
          if (!isPdf(file.name, file.type)) {
            setError(PDF_ERROR);
            return false;
          }
          return true;
        },
      }),
  );

  return (
    <UppyContextProvider uppy={uppy}>
      <FileDropzoneContent
        uppy={uppy}
        onFilesChange={onFilesChange}
        multiple={multiple}
        label={label}
        compact={compact}
        error={error}
        setError={setError}
      />
    </UppyContextProvider>
  );
}

type ContentProps = Props & {
  uppy: Uppy;
  error: string;
  setError: (error: string) => void;
};

function FileDropzoneContent({
  uppy,
  onFilesChange,
  multiple,
  label,
  compact,
  error,
  setError,
}: ContentProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const uppyFileState = useUppyState(uppy, (state) => state.files);
  const uppyFiles = useMemo(() => Object.values(uppyFileState), [uppyFileState]);
  const files = useMemo(
    () => uppyFiles.map((file) => file.data as File),
    [uppyFiles],
  );

  useEffect(() => {
    onFilesChange?.(files);
  }, [files, onFilesChange]);

  const prepareIncomingFiles = useCallback(
    (incoming: File[]) => {
      if (!multiple && incoming.length > 1) {
        setError(SINGLE_PDF_ERROR);
      } else setError("");

      if (!multiple) {
        const hasOneReplacement = incoming.length === 1 && uppy.getFiles().length === 1;
        uppy.setOptions({
          restrictions: { maxNumberOfFiles: hasOneReplacement ? 2 : 1 },
        });
      }
    },
    [multiple, setError, uppy],
  );

  const handleDropzoneDrop = useCallback(
    (incoming: File[]) => {
      setDragging(false);
      prepareIncomingFiles(incoming);
    },
    [prepareIncomingFiles],
  );
  const handleInputChange = useCallback(
    (incoming: File[]) => prepareIncomingFiles(incoming),
    [prepareIncomingFiles],
  );
  const dropzoneOptions = useMemo(
    () => ({
      noClick: true,
      onDragOver: () => setDragging(true),
      onDragEnter: () => setDragging(true),
      onDragLeave: () => setDragging(false),
      onDrop: handleDropzoneDrop,
      onFileInputChange: handleInputChange,
    }),
    [handleDropzoneDrop, handleInputChange],
  );
  const { getRootProps, getInputProps } = useDropzone(dropzoneOptions);
  const rootProps = getRootProps() as unknown as ButtonHTMLAttributes<HTMLButtonElement>;
  const uppyInputProps = getInputProps();
  const inputProps = uppyInputProps as InputHTMLAttributes<HTMLInputElement>;

  useEffect(() => {
    const onFilesAdded = (addedFiles: ReturnType<Uppy["getFiles"]>) => {
      if (!multiple && addedFiles.length) {
        const addedIds = new Set(addedFiles.map((file) => file.id));
        uppy
          .getFiles()
          .filter((file) => !addedIds.has(file.id))
          .forEach((file) => uppy.removeFile(file.id));
        uppy.setOptions({ restrictions: { maxNumberOfFiles: 1 } });
      }
    };
    const onRestrictionFailed = (file: ReturnType<Uppy["getFiles"]>[number] | undefined, error) => {
      if (!multiple) {
        uppy.setOptions({ restrictions: { maxNumberOfFiles: 1 } });

        if (error.message.includes('You can only upload')) {
          setError(SINGLE_PDF_ERROR);
        } else setError(PDF_ERROR);
      } else setError(PDF_ERROR);
    };

    uppy.on("files-added", onFilesAdded);
    uppy.on("restriction-failed", onRestrictionFailed);
    return () => {
      uppy.off("files-added", onFilesAdded);
      uppy.off("restriction-failed", onRestrictionFailed);
    };
  }, [multiple, setError, uppy]);

  function openPicker(replacing = false) {
    if (replacing) {
      uppy.setOptions({ restrictions: { maxNumberOfFiles: 2 } });
      window.addEventListener(
        "focus",
        () => window.setTimeout(() => uppy.setOptions({ restrictions: { maxNumberOfFiles: 1 } }), 0),
        { once: true },
      );
    }
    inputRef.current?.click();
  }

  function removeFile(index: number) {
    const file = uppyFiles[index];
    if (file) uppy.removeFile(file.id);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="dropzone-wrap">
      <input
        {...inputProps}
        ref={inputRef}
        className="visually-hidden"
        aria-label={label}
      />
      {!files.length && (
        <button
          {...rootProps}
          type="button"
          className={`dropzone${compact ? " dropzone-compact" : ""}${dragging ? " is-dragging" : ""}`}
          onClick={() => openPicker()}
          aria-describedby={error ? `${label.replaceAll(" ", "-")}-error` : undefined}
        >
          <CloudUpload
            className="cloud-icon"
            size={36}
            strokeWidth={1.7}
            aria-hidden="true"
          />
          <span className="drop-title">Drag and drop your PDF here</span>
          <span className="drop-browse">
            or <span>click to browse</span>
          </span>
          <span className="drop-hint">
            {multiple
              ? "PDF files only · You can select multiple files"
              : "PDF file only · One file (your complete answer copy)"}
          </span>
        </button>
      )}
      {error && (
        <p
          className="upload-error"
          id={`${label.replaceAll(" ", "-")}-error`}
          role="alert"
        >
          {error}
        </p>
      )}
      {!!files.length && !multiple && (
        <div className="selected-single" aria-live="polite">
          <FileText
            className="selected-single-icon"
            size={58}
            strokeWidth={1.35}
            aria-hidden="true"
          />
          <div className="single-file-details">
            <span className="single-file-name" title={files[0].name}>
              <span className="file-name-text">{files[0].name}</span>
              <small>{formatSize(files[0].size)}</small>
            </span>
            <button
              type="button"
              className="remove-file single-remove"
              aria-label={`Remove ${files[0].name}`}
              onClick={() => removeFile(0)}
            >
              <X size={15} />
            </button>
          </div>
          <button
            type="button"
            className="add-files-button replace-file-button"
            onClick={() => openPicker(true)}
          >
            Replace PDF
          </button>
        </div>
      )}
      {!!files.length && multiple && (
        <div className="selected-files" aria-live="polite">
          <p className="file-count">
            {files.length} PDF{files.length === 1 ? "" : "s"} selected
          </p>
          {files.map((file, index) => (
            <div
              className="selected-file"
              key={`${uppyFiles[index].id}`}
            >
              <FileText
                className="multi-file-icon"
                size={25}
                strokeWidth={1.5}
                aria-hidden="true"
              />
              <span className="selected-file-name" title={file.name}>
                <span className="file-name-text">{file.name}</span>
                <small>{formatSize(file.size)}</small>
              </span>
              <button
                type="button"
                className="remove-file"
                aria-label={`Remove ${file.name}`}
                onClick={() => removeFile(index)}
              >
                <X size={15} />
              </button>
            </div>
          ))}
          <button
            type="button"
            className="add-files-button"
            onClick={() => openPicker()}
          >
            <Plus size={14} /> Add PDFs
          </button>
        </div>
      )}
    </div>
  );
}
