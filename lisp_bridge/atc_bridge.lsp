; ================================================================
; Datei: atc_bridge.lsp
; Zweck: Universelle Brucke zwischen AutoLISP und Python uber JSON.
; Sprache: Deutsch
; ================================================================

(vl-load-com)

; ------------------------------------------------------------
; Dienstfunktionen
; ------------------------------------------------------------
(defun atc-log (msg)
  (princ (strcat "\n[ATC-Bridge] " msg))
)

(defun atc-read-file (fname / f line data)
  (if (findfile fname)
    (progn
      (setq f (open fname "r"))
      (setq data "")
      (while (setq line (read-line f))
        (setq data (strcat data line)))
      (close f)
      data)
    nil)
)

(defun atc-write-file (fname text / f)
  (setq f (open fname "w"))
  (if f
    (progn (write-line text f) (close f) T)
    nil)
)

; ------------------------------------------------------------
; JSON Hilfsfunktionen (primitive)
; ------------------------------------------------------------
(defun atc-json-escape (s)
  (if s
    (vl-string-subst "\\\"" "\"" (vl-string-subst "\\\\" "\\" s))
    "")
)

(defun atc-json-point (pt)
  (if pt
    (strcat "{\"x\": " (rtos (car pt) 2 6)
            ", \"y\": " (rtos (cadr pt) 2 6)
            ", \"z\": " (rtos (caddr pt) 2 6) "}")
    "{\"cancelled\": true}")
)

(defun atc-json-entity (ename)
  (if ename
    (let* ((edata (entget ename))
           (handle (cdr (assoc 5 edata)))
           (layer (cdr (assoc 8 edata)))
           (etype (cdr (assoc 0 edata))))
      (strcat "{\"entity\": {"
              "\"handle\": \"" handle "\", "
              "\"layer\": \"" (atc-json-escape layer) "\", "
              "\"type\": \"" etype "\"}}"))
    "{\"cancelled\": true}")
)

; ------------------------------------------------------------
; Hauptpfade
; ------------------------------------------------------------
(setq base "E:\\AT-CAD\\") ; ggf. anpassen
(setq reqFile  (strcat base "lisp_bridge\\request.json"))
(setq respFile (strcat base "lisp_bridge\\response.json"))

; ------------------------------------------------------------
; Hauptfunktion – Aufruf von Python-Seite
; ------------------------------------------------------------
(defun c:ATC_PROCESS_REQUEST ( / reqData)
  (atc-log "Starte Anfrageverarbeitung...")

  (setq reqData (atc-read-file reqFile))
  (if (not reqData)
    (progn
      (atc-log "Keine Anfrage gefunden.")
      (princ))
    (progn
      (cond
        ((vl-string-search "get_point" reqData)
         (atc-log "> get_point angefordert.")
         (setq pt (getpoint "\nWahlen Sie einen Punkt: "))
         (atc-write-file respFile (atc-json-point pt))
         (if pt
           (atc-log "Punkt erfolgreich gespeichert.")
           (atc-log "Punktauswahl abgebrochen."))
        )

        ((vl-string-search "get_entity" reqData)
         (atc-log "> get_entity angefordert.")
         (setq sel (entsel "\nWahlen Sie ein Objekt: "))
         (if sel
           (atc-write-file respFile (atc-json-entity (car sel)))
           (atc-write-file respFile "{\"cancelled\": true}"))
         (atc-log "Objektauswahl abgeschlossen.")
        )

        ((vl-string-search "get_distance" reqData)
         (atc-log "> get_distance angefordert.")
         (setq p1 (getpoint "\nErster Punkt: "))
         (if p1
           (progn
             (setq p2 (getpoint p1 "\nZweiter Punkt: "))
             (if p2
               (progn
                 (setq dist (distance p1 p2))
                 (atc-write-file respFile
                   (strcat "{\"distance\": " (rtos dist 2 6)
                           ", \"points\": ["
                           (rtos (car p1) 2 6) ", "
                           (rtos (cadr p1) 2 6) ", "
                           (rtos (caddr p1) 2 6) ", "
                           (rtos (car p2) 2 6) ", "
                           (rtos (cadr p2) 2 6) ", "
                           (rtos (caddr p2) 2 6) "]}"))
                 (atc-log "Abstand berechnet und gespeichert."))
               (atc-write-file respFile "{\"cancelled\": true}")))
           (atc-write-file respFile "{\"cancelled\": true}"))
        )

        ((vl-string-search "get_text" reqData)
         (atc-log "> get_text angefordert.")
         (setq txt (getstring T "\nGeben Sie den Text ein: "))
         (if (and txt (/= txt ""))
           (atc-write-file respFile (strcat "{\"text\": \"" (atc-json-escape txt) "\"}"))
           (atc-write-file respFile "{\"cancelled\": true}"))
        )

        ((vl-string-search "set_layer" reqData)
         (atc-log "> set_layer angefordert.")
         (setq lname (getstring T "\nNeuer Layername: "))
         (if (and lname (/= lname ""))
           (progn
             (command "_-layer" "M" lname "")
             (atc-write-file respFile (strcat "{\"status\": \"ok\", \"layer\": \"" lname "\"}"))
             (atc-log (strcat "Layer " lname " erstellt und aktuell gesetzt.")))
           (atc-write-file respFile "{\"cancelled\": true}"))
        )

        ((vl-string-search "ping" reqData)
         (atc-log "> ping empfangen.")
         (atc-write-file respFile "{\"status\": \"ok\", \"message\": \"pong\"}")
        )

        ((vl-string-search "load_lisp" reqData)
         (atc-log "> load_lisp angefordert (nichts zu laden – bereits aktiv).")
         (atc-write-file respFile "{\"status\": \"ok\", \"message\": \"LISP-Modul aktiv\"}")
        )

        (T
         (atc-log "> Unbekannter Befehl.")
         (atc-write-file respFile "{\"error\": \"unbekannter Befehl\"}")
        )
      )

      ;; Anfrage loschen, um Wiederholungen zu vermeiden
      (if (findfile reqFile) (vl-file-delete reqFile))
    )
  )
  (princ)
)

; ------------------------------------------------------------
; Hilfskommandos
; ------------------------------------------------------------
(defun c:ATC_LOAD_BRIDGE ()
  (princ "\n[ATC] LISP-Bridge wurde erfolgreich geladen.")
  (princ)
)

(princ "\n[ATC] atc_bridge.lsp geladen. Verwenden Sie den Befehl ATC_PROCESS_REQUEST fur Python-Kommunikation.")
(princ)
