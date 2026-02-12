import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { IconX, IconFileText, IconDownload } from '@tabler/icons-react';
import './DocumentModal.css';

interface DocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  filename: string | null;
  content: string | null;
  isLoading: boolean;
  onDownload: () => void;
}

export function DocumentModal({
  isOpen,
  onClose,
  filename,
  content,
  isLoading,
  onDownload
}: DocumentModalProps) {
  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className="modal-content">
          {/* Header */}
          <div className="modal-header">
            <div className="modal-title">
              <IconFileText size={20} />
              <Dialog.Title>{filename || 'Documento'}</Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button className="modal-close" aria-label="Cerrar">
                <IconX size={20} />
              </button>
            </Dialog.Close>
          </div>

          {/* Content */}
          <div className="modal-body">
            {isLoading ? (
              <div className="modal-loading">
                <div className="spinner"></div>
                <p>Cargando documento...</p>
              </div>
            ) : content ? (
              <>
                <div className="modal-info">
                  <span className="modal-badge">
                    {content.length.toLocaleString()} caracteres
                  </span>
                  <button className="modal-download-btn" onClick={onDownload}>
                    <IconDownload size={14} />
                    Descargar
                  </button>
                </div>
                <div className="modal-text-content">
                  <pre>{content}</pre>
                </div>
              </>
            ) : (
              <div className="modal-error">
                <p>No se pudo cargar el contenido del documento</p>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
