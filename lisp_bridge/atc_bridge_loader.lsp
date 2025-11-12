; ================================================================
; Datei: atc_bridge_loader.lsp
; Zweck:
;   Automatische Initialisierung der AT-CAD Bridge zwischen AutoLISP und Python.
;   Ladt "atc_bridge.lsp" beim Start von AutoCAD.
; Sprache: Deutsch
; ================================================================

(vl-load-com)

(defun atc-log (msg)
  (princ (strcat "\n[ATC-Loader] " msg))
)

(defun c:ATC_BRIDGE_START (/ base bridgeFile)
  (setq base "E:\\AT-CAD\\lisp_bridge\\") ; >>> ANPASSEN falls anderes Projektverzeichnis
  (setq bridgeFile (strcat base "atc_bridge.lsp"))

  (if (findfile bridgeFile)
    (progn
      (load bridgeFile)
      (atc-log (strcat "Bridge geladen: " bridgeFile))
      (princ "\n[ATC] Verwenden Sie Befehl ATC_PROCESS_REQUEST fur Python-Kommunikation.")
    )
    (princ (strcat "\n[ATC] Fehler: Datei nicht gefunden: " bridgeFile))
  )
  (princ)
)

; ------------------------------------------------------------
; Automatische Initialisierung beim Laden
; ------------------------------------------------------------
(defun-q atc-auto-load-bridge (/)
  (atc-log "Initialisierung...")
  (c:ATC_BRIDGE_START)
  (atc-log "Initialisierung abgeschlossen.")
  (princ)
)

(atc-auto-load-bridge)

(princ "\n[ATC] Automatischer Bridge-Loader aktiviert.")
(princ)
