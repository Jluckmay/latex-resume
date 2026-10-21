"""Extratores automáticos de dados para GitHub, ORCID, Lattes, LinkedIn e Portfólio com proteção anti-SSRF e anti-DoS."""

from __future__ import annotations

import io
import ipaddress
import re
import socket
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

_MAX_HTTP_BYTES = 1_500_000  # 1.5 MB max download size for external pages
_MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024  # 10 MB max upload size
_MAX_UNCOMPRESSED_XML_BYTES = 15 * 1024 * 1024  # 15 MB max uncompressed Lattes XML

def parse_linkedin_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do LinkedIn para (url_completa, nick).
    Aceita URL completa (https://linkedin.com/in/nick), in/nick, @nick ou apenas nick.
    """
    v = str(val or "").strip().lstrip("@")
    if not v:
        return "", ""
    m = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in/)?([a-zA-Z0-9_\-%]+)", v, re.IGNORECASE)
    if m:
        nick = m.group(1).strip("/")
        return f"https://www.linkedin.com/in/{nick}", nick
    if v.lower().startswith("in/"):
        nick = v[3:].strip("/")
        return f"https://www.linkedin.com/in/{nick}", nick
    if v.startswith(("http://", "https://")):
        clean_v = v.rstrip("/")
        parts = clean_v.split("/")
        nick = parts[-1] if parts else clean_v
        return clean_v, nick
    nick = v.strip("/")
    return f"https://www.linkedin.com/in/{nick}", nick


def parse_lattes_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do Lattes para (url_completa, id_lattes).
    Aceita ID de 16 dígitos, ID alfanumérico K-code, URL lattes.cnpq.br ou buscatextual.
    """
    v = str(val or "").strip()
    if not v:
        return "", ""
    m16 = re.search(r"\b(\d{16})\b", v)
    if m16:
        lid = m16.group(1)
        return f"http://lattes.cnpq.br/{lid}", lid
    m_id = re.search(r"[?&]id=([A-Za-z0-9]+)", v)
    if m_id:
        lid = m_id.group(1)
        u = v if v.startswith(("http://", "https://")) else f"http://{v}"
        return u, lid
    if v.startswith(("http://", "https://")):
        parts = v.rstrip("/").split("/")
        lid = parts[-1] if parts else v
        return v, lid
    if "lattes.cnpq.br" in v.lower():
        parts = v.rstrip("/").split("/")
        lid = parts[-1] if parts else v
        return f"http://{v}", lid
    lid = v.strip("/")
    return f"http://lattes.cnpq.br/{lid}", lid


def parse_github_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do GitHub para (url_completa, username_nick)."""
    v = str(val or "").strip().lstrip("@")
    if not v:
        return "", ""
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_\-%]+)", v, re.IGNORECASE)
    if m:
        nick = m.group(1).strip("/")
        return f"https://github.com/{nick}", nick
    if v.startswith(("http://", "https://")):
        parts = v.rstrip("/").split("/")
        nick = parts[-1] if parts else v
        return v, nick
    nick = v.strip("/")
    return f"https://github.com/{nick}", nick


def parse_orcid_input(val: str) -> Tuple[str, str]:
    """Normaliza o input do ORCID para (url_completa, orcid_id)."""
    v = str(val or "").strip()
    if not v:
        return "", ""
    m = re.search(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b", v, re.IGNORECASE)
    if m:
        oid = m.group(1).upper()
        return f"https://orcid.org/{oid}", oid
    if v.startswith(("http://", "https://")):
        parts = v.rstrip("/").split("/")
        oid = parts[-1] if parts else v
        return v, oid
    oid = v.strip("/")
    return f"https://orcid.org/{oid}", oid



def _is_safe_public_url(url: str, allowed_domain_suffixes: tuple[str, ...] | None = None) -> tuple[bool, str]:
    """Valida URL contra ataques de SSRF (bloqueia loopback, redes privadas, link-local/metadata AWS/GCP)."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False, "URL malformada"

    if parsed.scheme not in ("http", "https"):
        return False, "Esquema de URL não permitido (use http ou https)"

    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname or hostname in ("localhost", "0.0.0.0", "broadcasthost") or hostname.endswith(".local") or hostname.endswith(".internal"):
        return False, "Host local ou interno bloqueado por política anti-SSRF"

    if allowed_domain_suffixes:
        if not any(hostname == d or hostname.endswith("." + d) for d in allowed_domain_suffixes):
            return False, "Domínio não pertence à lista permitida para esta fonte"

    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except Exception:
        return False, "Não foi possível resolver o DNS do domínio informado"

    if not addr_infos:
        return False, "Sem endereço IP público associado ao domínio"

    for info in addr_infos:
        ip_str = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, "Endereço IP inválido"
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
            or not ip_obj.is_global
        ):
            return False, "Endereço IP privado/interno bloqueado por política anti-SSRF"

    return True, parsed.geturl()


def _safe_http_get(
    url: str,
    timeout: int = 8,
    allowed_domain_suffixes: tuple[str, ...] | None = None,
    max_redirects: int = 3,
) -> Tuple[int, str, str]:
    """Executa GET HTTP validando cada redirecionamento contra SSRF e limitando o tamanho da resposta."""
    current_url = url.strip()
    session = requests.Session()
    session.trust_env = False

    try:
        for _ in range(max_redirects + 1):
            ok, checked_or_err = _is_safe_public_url(current_url, allowed_domain_suffixes)
            if not ok:
                return 0, "", checked_or_err

            with session.get(
                checked_or_err,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            ) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location")
                    if not loc:
                        return resp.status_code, "", "Redirecionamento inválido"
                    current_url = urllib.parse.urljoin(checked_or_err, loc)
                    continue

                chunks: list[bytes] = []
                total = 0
                for chunk in resp.iter_content(chunk_size=16384):
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _MAX_HTTP_BYTES:
                        break
                    chunks.append(chunk)
                raw_bytes = b"".join(chunks)
                enc = resp.encoding or "utf-8"
                text = raw_bytes.decode(enc, errors="ignore")
                return resp.status_code, text, ""
        return 0, "", "Número máximo de redirecionamentos excedido"
    except Exception as exc:
        return 0, "", f"Erro de conexão ({type(exc).__name__})"
    finally:
        session.close()


def extract_github(github_input: str) -> Dict[str, Any]:
    """Extrai perfil, linguagens e principais repositórios públicos via API do GitHub."""
    if not github_input or not github_input.strip():
        return {}

    cleaned = github_input.strip().rstrip("/")
    match = re.search(r"github\.com/([A-Za-z0-9_.-]+)", cleaned, re.IGNORECASE)
    username = match.group(1) if match else cleaned.lstrip("@").split("/")[0]
    username = re.sub(r"[^A-Za-z0-9-]", "", username)[:39]
    if not username:
        return {"error": "Usuário GitHub inválido"}

    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    result: Dict[str, Any] = {
        "username": username,
        "url": f"https://github.com/{username}",
    }

    try:
        r_user = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=10)
        if r_user.status_code != 200:
            result["error"] = f"HTTP {r_user.status_code}"
            return result

        u = r_user.json()
        result.update(
            {
                "name": u.get("name") or "",
                "bio": u.get("bio") or "",
                "company": u.get("company") or "",
                "location": u.get("location") or "",
                "blog": u.get("blog") or "",
                "email": u.get("email") or "",
                "avatar_url": u.get("avatar_url") or "",
                "public_repos": u.get("public_repos") or 0,
                "followers": u.get("followers") or 0,
            }
        )

        r_repos = requests.get(
            f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30",
            headers=headers,
            timeout=10,
        )
        repos_data = r_repos.json() if r_repos.status_code == 200 and isinstance(r_repos.json(), list) else []

        own_repos = [r for r in repos_data if isinstance(r, dict) and not r.get("fork")]
        own_repos.sort(
            key=lambda x: (x.get("stargazers_count", 0), x.get("updated_at", "")),
            reverse=True,
        )

        lang_counter: Counter[str] = Counter()
        repos_summary: List[Dict[str, Any]] = []
        for repo in own_repos[:10]:
            lang = repo.get("language") or ""
            if lang:
                lang_counter[lang] += 1
            repos_summary.append(
                {
                    "name": repo.get("name") or "",
                    "description": repo.get("description") or "",
                    "language": lang,
                    "stars": repo.get("stargazers_count") or 0,
                    "url": repo.get("html_url") or "",
                    "topics": (repo.get("topics") or [])[:5],
                }
            )

        result["top_languages"] = [lang for lang, _ in lang_counter.most_common(8)]
        result["repos"] = repos_summary
    except Exception as exc:
        result["error"] = f"Falha ao consultar GitHub ({type(exc).__name__})"

    return result


def extract_orcid(orcid_input: str) -> Dict[str, Any]:
    """Extrai dados públicos do pesquisador via API v3.0 do ORCID."""
    if not orcid_input or not orcid_input.strip():
        return {}

    match = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", orcid_input.upper())
    if not match:
        return {"raw_input": orcid_input.strip(), "error": "Formato ORCID inválido"}

    orcid_id = match.group(1)
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    result: Dict[str, Any] = {
        "orcid_id": orcid_id,
        "url": f"https://orcid.org/{orcid_id}",
        "educations": [],
        "employments": [],
        "works": [],
    }

    try:
        r = requests.get(f"https://pub.orcid.org/v3.0/{orcid_id}/record", headers=headers, timeout=12)
        if r.status_code != 200:
            result["error"] = f"HTTP {r.status_code}"
            return result

        data = r.json()
        person = data.get("person") or {}
        name_obj = person.get("name") or {}
        given = (name_obj.get("given-names") or {}).get("value") or ""
        family = (name_obj.get("family-name") or {}).get("value") or ""
        credit = (name_obj.get("credit-name") or {}).get("value") or ""
        result["name"] = credit or f"{given} {family}".strip()
        result["bio"] = ((person.get("biography") or {}).get("content")) or ""

        activities = data.get("activities-summary") or {}

        # Educations
        edu_groups = ((activities.get("educations") or {}).get("affiliation-group")) or []
        for grp in edu_groups:
            for s in grp.get("summaries") or []:
                ed = s.get("education-summary") or {}
                result["educations"].append(_parse_orcid_affiliation(ed))

        # Employments
        emp_groups = ((activities.get("employments") or {}).get("affiliation-group")) or []
        for grp in emp_groups:
            for s in grp.get("summaries") or []:
                em = s.get("employment-summary") or {}
                result["employments"].append(_parse_orcid_affiliation(em))

        # Works / Publications
        work_groups = ((activities.get("works") or {}).get("group")) or []
        for grp in work_groups[:20]:
            summaries = grp.get("work-summary") or []
            if not summaries:
                continue
            w = summaries[0]
            title = (((w.get("title") or {}).get("title") or {}).get("value")) or ""
            journal = ((w.get("journal-title") or {}).get("value")) or ""
            pub_date = w.get("publication-date") or {}
            year = ((pub_date.get("year") or {}).get("value")) or ""
            doi = ""
            ext_ids = ((w.get("external-ids") or {}).get("external-id")) or []
            for eid in ext_ids:
                if (eid.get("external-id-type") or "").lower() == "doi":
                    doi = eid.get("external-id-value") or ""
                    break
            if title:
                result["works"].append(
                    {"title": title, "journal": journal, "year": year, "doi": doi}
                )
    except Exception as exc:
        result["error"] = f"Falha ao consultar ORCID ({type(exc).__name__})"

    return result


def _parse_orcid_affiliation(item: Dict[str, Any]) -> Dict[str, str]:
    role = item.get("role-title") or ""
    dept = item.get("department-name") or ""
    deg = role or dept or ""
    org = ((item.get("organization") or {}).get("name")) or ""
    start_yr = (((item.get("start-date") or {}).get("year") or {}).get("value")) or ""
    end_yr = (((item.get("end-date") or {}).get("year") or {}).get("value")) or "Atual"
    return {
        "role": role,
        "dept": dept,
        "degree": deg,
        "course": deg,
        "org": org,
        "organization": org,
        "institution": org,
        "school": org,
        "company": org,
        "start": start_yr,
        "end": end_yr,
    }


def _strip_accents(s: str) -> str:
    """Remove acentos para comparação robusta de strings insensível a diacríticos."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if unicodedata.category(c) != "Mn").lower()


_KNOWN_LANGS_CANONICAL: Dict[str, str] = {
    "ingles": "Inglês",
    "english": "English",
    "portugues": "Português",
    "portuguese": "Portuguese",
    "espanhol": "Espanhol",
    "spanish": "Spanish",
    "frances": "Francês",
    "french": "French",
    "alemao": "Alemão",
    "german": "German",
    "italiano": "Italiano",
    "italian": "Italian",
    "japones": "Japonês",
    "japanese": "Japanese",
    "chines": "Chinês",
    "chinese": "Chinese",
    "mandarim": "Mandarim",
    "mandarin": "Mandarin",
    "russo": "Russo",
    "russian": "Russian",
    "arabe": "Árabe",
    "arabic": "Arabic",
    "coreano": "Coreano",
    "korean": "Korean",
    "holandes": "Holandês",
    "dutch": "Dutch",
    "sueco": "Sueco",
    "swedish": "Swedish",
    "polones": "Polonês",
    "polish": "Polish",
    "hebraico": "Hebraico",
    "hebrew": "Hebrew",
    "grego": "Grego",
    "greek": "Greek",
    "latim": "Latim",
    "latin": "Latin",
}


def extract_languages_from_text(text: str) -> List[str]:
    """Extrai idiomas estruturados com proficiência de textos livres (LinkedIn PDF, Lattes texto/PDF, anotações)."""
    if not text:
        return []

    results: List[str] = []
    candidate_lines: List[str] = []

    # 1. Seção estruturada de Idiomas / Languages
    sec_match = re.search(
        r"(?:^|\n)\s*(?:Idiomas|Languages|Línguas|Lingua|Idioma)\s*[:\n](.+?)(?=(?:\n\s*(?:Formação|Educação|Education|Atuação|Experiência|Experience|Projetos|Projects|Publicações|Publications|Produção|Prêmios|Premios|Awards|Certificados|Certifications|Competências|Skills)\b|\Z))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if sec_match:
        sec_text = sec_match.group(1).strip()
        candidate_lines.extend([l.strip() for l in sec_text.splitlines() if l.strip()])

    # 2. Linha inline 'Idiomas: Inglês (Fluente), Espanhol...'
    for m in re.finditer(r"(?:Idiomas|Languages|Línguas)\s*:\s*([^\n\r]+)", text, re.IGNORECASE):
        items = re.split(r"[,;]\s*", m.group(1))
        candidate_lines.extend(items)

    for line in candidate_lines:
        line_clean = re.sub(r"^[•\-\*,]\s*", "", line).strip()
        if not line_clean:
            continue
        first_token = line_clean.split()[0].rstrip(":,;()")
        first_norm = _strip_accents(first_token)
        if first_norm in _KNOWN_LANGS_CANONICAL:
            lang_label = _KNOWN_LANGS_CANONICAL[first_norm]
            low = line_clean.lower()
            if "compreende" in low:
                prof = (
                    "Avançado"
                    if ("bem" in low or "fluente" in low)
                    else ("Intermediário" if "razoavel" in low else "Básico")
                )
                results.append(f"{lang_label} ({prof})")
            elif "(" in line_clean and ")" in line_clean:
                paren_part = line_clean[line_clean.find("(") : line_clean.rfind(")") + 1]
                results.append(f"{lang_label} {paren_part}")
            elif " - " in line_clean or ": " in line_clean:
                sep = " - " if " - " in line_clean else ": "
                parts = line_clean.split(sep, 1)
                results.append(f"{lang_label} ({parts[1].strip()})")
            else:
                rem = line_clean[len(first_token) :].strip()
                if rem:
                    results.append(f"{lang_label} ({rem})")
                else:
                    results.append(lang_label)

    # Deduplica preservando ordem de aparição
    seen: set[str] = set()
    dedup: List[str] = []
    for r in results:
        key = _strip_accents(r.split()[0])
        if key not in seen:
            seen.add(key)
            dedup.append(r)
    return dedup


def extract_lattes(
    lattes_url: str = "",
    file_bytes: bytes | None = None,
    filename: str = "",
    pasted_text: str = "",
) -> Dict[str, Any]:
    """Extrai dados do Currículo Lattes a partir de XML/ZIP oficial, PDF/HTML, URL ou texto."""
    norm_url, lid = parse_lattes_input(lattes_url)
    result: Dict[str, Any] = {
        "url": norm_url,
        "lattes_id": lid,
        "educations": [],
        "employments": [],
        "publications": [],
        "projects": [],
        "languages": [],
        "awards": [],
    }

    # 1. Se o usuário enviou XML ou ZIP exportado do Lattes (com proteção contra ZIP Bomb e XXE)
    if file_bytes:
        if len(file_bytes) > _MAX_UPLOAD_FILE_BYTES:
            result["parse_warning"] = "Arquivo Lattes excede o limite de 10 MB."
            return result
        fname_lower = (filename or "").lower()
        try:
            if fname_lower.endswith(".zip") or file_bytes[:2] == b"PK":
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    xml_infos = [i for i in zf.infolist() if i.filename.lower().endswith(".xml")]
                    if xml_infos:
                        info = xml_infos[0]
                        if info.file_size > _MAX_UNCOMPRESSED_XML_BYTES:
                            raise ValueError("Arquivo XML descompactado excede o limite de segurança (15 MB).")
                        xml_bytes = zf.read(info.filename)
                        _parse_lattes_xml(xml_bytes, result)
            elif fname_lower.endswith(".xml") or b"<CURRICULO-VITAE" in file_bytes[:1000]:
                _parse_lattes_xml(file_bytes, result)
            elif fname_lower.endswith(".pdf") or file_bytes[:4] == b"%PDF":
                result["raw_text"] = _extract_pdf_text(file_bytes)
            else:
                soup = BeautifulSoup(file_bytes.decode("utf-8", errors="ignore"), "html.parser")
                result["raw_text"] = soup.get_text(" ", strip=True)[:5000]
        except Exception as exc:
            result["parse_warning"] = f"Aviso ao ler arquivo Lattes ({type(exc).__name__})"

    # 2. Se há texto colado
    if pasted_text and pasted_text.strip():
        existing = result.get("raw_text", "")
        result["raw_text"] = (existing + "\n" + pasted_text.strip()[:8000]).strip()

    # 3. Se informou apenas URL e ainda não há dados extraídos, tenta buscar página pública do CNPq
    if norm_url and not result["educations"] and not result.get("raw_text"):
        status_code, html_text, _ = _safe_http_get(
            norm_url,
            timeout=8,
            allowed_domain_suffixes=("cnpq.br",),
        )
        if status_code == 200 and html_text and "captcha" not in html_text.lower():
            soup = BeautifulSoup(html_text, "html.parser")
            txt = soup.get_text(" ", strip=True)
            if len(txt) > 200:
                result["raw_text"] = txt[:4000]

    if not result["languages"] and result.get("raw_text"):
        result["languages"] = extract_languages_from_text(result["raw_text"])

    return result


def _parse_lattes_xml(xml_bytes: bytes, out: Dict[str, Any]) -> None:
    """Faz o parse estruturado do XML oficial da Plataforma Lattes (`CURRICULO-VITAE`) com bloqueio de DTD/Entities."""
    if len(xml_bytes) > _MAX_UNCOMPRESSED_XML_BYTES:
        raise ValueError("XML excede o tamanho máximo permitido.")
    # Detecta codificação a partir da declaração XML ou tenta UTF-8 e ISO-8859-1
    encoding_match = re.search(rb'encoding=["\']([a-zA-Z0-9_\-]+)["\']', xml_bytes[:200])
    declared_enc = encoding_match.group(1).decode("ascii", errors="ignore").lower() if encoding_match else ""
    if declared_enc in ("iso-8859-1", "latin-1", "latin1"):
        text = xml_bytes.decode("iso-8859-1", errors="replace")
    else:
        try:
            text = xml_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = xml_bytes.decode("iso-8859-1", errors="replace")

    if re.search(r"<!\s*(ENTITY|DOCTYPE)\b", text[:4096], flags=re.IGNORECASE):
        raise ValueError("Declarações DTD/ENTITY bloqueadas por segurança (anti-XXE).")

    root = ET.fromstring(text)
    id_lattes = root.attrib.get("NUMERO-IDENTIFICADOR", "")
    if id_lattes:
        out["lattes_id"] = id_lattes
        if not out.get("url"):
            out["url"] = f"http://lattes.cnpq.br/{id_lattes}"

    dados_gerais = root.find("DADOS-GERAIS")
    if dados_gerais is not None:
        out["name"] = dados_gerais.attrib.get("NOME-COMPLETO", "")
        resumo = dados_gerais.find("RESUMO-CV")
        if resumo is not None:
            out["summary"] = resumo.attrib.get("TEXTO-RESUMO-CV-RH", "")

        # Formação acadêmica
        formacao = dados_gerais.find("FORMACAO-ACADEMICA-TITULACAO")
        if formacao is not None:
            level_map = {
                "DOUTORADO": "Doutorado",
                "MESTRADO": "Mestrado",
                "MESTRADO-PROFISSIONALIZANTE": "Mestrado Profissional",
                "ESPECIALIZACAO": "Especialização",
                "GRADUACAO": "Graduação",
                "POS-DOUTORADO": "Pós-Doutorado",
            }
            for tag, label in level_map.items():
                for node in formacao.findall(tag):
                    out["educations"].append(
                        {
                            "level": label,
                            "course": node.attrib.get("NOME-CURSO", ""),
                            "institution": node.attrib.get("NOME-INSTITUICAO", ""),
                            "start": node.attrib.get("ANO-DE-INICIO", ""),
                            "end": node.attrib.get("ANO-DE-CONCLUSAO", "") or "Atual",
                            "thesis_title": (
                                node.attrib.get("TITULO-DA-DISSERTACAO-TESE", "")
                                or node.attrib.get("TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO", "")
                            ),
                        }
                    )

        # Atuações profissionais
        atuacoes = dados_gerais.find("ATUACOES-PROFISSIONAIS")
        if atuacoes is not None:
            for ap in atuacoes.findall("ATUACAO-PROFISSIONAL"):
                inst = ap.attrib.get("NOME-INSTITUICAO", "")
                for vinc in ap.findall(".//VINCULOS"):
                    out["employments"].append(
                        {
                            "institution": inst,
                            "role": (
                                vinc.attrib.get("OUTRO-ENQUADRAMENTO-FUNCIONAL-INFORMADO", "")
                                or vinc.attrib.get("ENQUADRAMENTO-FUNCIONAL", "")
                            ),
                            "start": vinc.attrib.get("ANO-INICIO", ""),
                            "end": vinc.attrib.get("ANO-FIM", "") or "Atual",
                            "description": vinc.attrib.get("OUTRAS-INFORMACOES", ""),
                        }
                    )

                # Projetos de pesquisa
                for proj in ap.findall(".//PROJETO-DE-PESQUISA"):
                    out["projects"].append(
                        {
                            "title": proj.attrib.get("NOME-DO-PROJETO", ""),
                            "year": proj.attrib.get("ANO-INICIO", ""),
                            "description": proj.attrib.get("DESCRICAO-DO-PROJETO", ""),
                        }
                    )

        # Idiomas (suporte completo a IDIOMA e DESCRICAO-DO-IDIOMA do CNPq)
        idiomas = dados_gerais.find("IDIOMAS")
        if idiomas is not None:
            prof_map = {
                "bom": "Avançado",
                "lê bem": "Avançado",
                "fala bem": "Avançado",
                "muito_bom": "Fluente",
                "excelente": "Fluente",
                "fluente": "Fluente",
                "regular": "Intermediário",
                "razoavel": "Intermediário",
                "lê razoavel": "Intermediário",
                "fala razoavel": "Intermediário",
                "intermediário": "Intermediário",
                "intermediario": "Intermediário",
                "pouco": "Básico",
                "lê pouco": "Básico",
                "fala pouco": "Básico",
                "iniciante": "Básico",
                "básico": "Básico",
                "basico": "Básico",
                "nenhum": "",
            }
            for idm in idiomas.findall("IDIOMA"):
                raw_name = (
                    idm.attrib.get("DESCRICAO-DO-IDIOMA", "").strip()
                    or idm.attrib.get("IDIOMA", "").strip()
                    or idm.attrib.get("NOME-DO-IDIOMA", "").strip()
                )
                if not raw_name:
                    continue
                norm_key = _strip_accents(raw_name)
                if norm_key == "outro":
                    raw_name = idm.attrib.get("DESCRICAO-DO-IDIOMA", "").strip() or "Outro"
                    norm_key = _strip_accents(raw_name)
                display_name = _KNOWN_LANGS_CANONICAL.get(norm_key, raw_name)

                leit = prof_map.get(idm.attrib.get("PROFICIENCIA-DE-LEITURA", "").strip().lower(), "")
                fala = prof_map.get(idm.attrib.get("PROFICIENCIA-DE-FALA", "").strip().lower(), "")
                comp = prof_map.get(idm.attrib.get("PROFICIENCIA-DE-COMPREENSAO", "").strip().lower(), "")

                if leit and fala and leit == fala:
                    prof_str = leit
                elif fala:
                    prof_str = fala
                elif leit:
                    prof_str = f"Leitura: {leit}"
                elif comp:
                    prof_str = comp
                else:
                    prof_str = ""

                entry = f"{display_name} ({prof_str})" if prof_str else display_name
                out["languages"].append(entry)

        # Prêmios e títulos
        premios = dados_gerais.find("PREMIOS-TITULOS")
        if premios is not None:
            for pr in premios.findall("PREMIO-TITULO"):
                nome_pr = pr.attrib.get("NOME-DO-PREMIO-OU-TITULO", "")
                ano_pr = pr.attrib.get("ANO-DA-PREMIACAO", "")
                ent_pr = pr.attrib.get("NOME-DA-ENTIDADE-PROMOTORA", "")
                if nome_pr:
                    out["awards"].append(f"{nome_pr} - {ent_pr} ({ano_pr})")

    # Produção bibliográfica
    prod = root.find("PRODUCAO-BIBLIOGRAFICA")
    if prod is not None:
        for art in prod.findall(".//ARTIGO-PUBLICADO"):
            basico = art.find("DADOS-BASICOS-DO-ARTIGO")
            det = art.find("DETALHAMENTO-DO-ARTIGO")
            autores = [
                a.attrib.get("NOME-PARA-CITACAO", "")
                for a in art.findall("AUTORES")
                if a.attrib.get("NOME-PARA-CITACAO")
            ]
            if basico is not None:
                out["publications"].append(
                    {
                        "title": basico.attrib.get("TITULO-DO-ARTIGO", ""),
                        "year": basico.attrib.get("ANO-DO-ARTIGO", ""),
                        "doi": basico.attrib.get("DOI", ""),
                        "venue": det.attrib.get("TITULO-DO-PERIODICO-OU-REVISTA", "") if det is not None else "",
                        "authors": "; ".join(autores[:5]),
                    }
                )

        for trab in prod.findall(".//TRABALHO-EM-EVENTOS")[:10]:
            basico = trab.find("DADOS-BASICOS-DO-TRABALHO")
            det = trab.find("DETALHAMENTO-DO-TRABALHO")
            if basico is not None:
                out["publications"].append(
                    {
                        "title": basico.attrib.get("TITULO-DO-TRABALHO", ""),
                        "year": basico.attrib.get("ANO-DO-TRABALHO", ""),
                        "doi": basico.attrib.get("DOI", ""),
                        "venue": det.attrib.get("NOME-DO-EVENTO", "") if det is not None else "",
                        "authors": "",
                    }
                )


def extract_linkedin(
    linkedin_url: str = "",
    file_bytes: bytes | None = None,
    pasted_text: str = "",
) -> Dict[str, Any]:
    """Extrai dados do LinkedIn a partir de URL, PDF exportado ('Salvar como PDF') ou texto."""
    norm_url, li_nick = parse_linkedin_input(linkedin_url)
    result: Dict[str, Any] = {"url": norm_url, "linkedin_nick": li_nick, "languages": []}

    if file_bytes:
        if len(file_bytes) > _MAX_UPLOAD_FILE_BYTES:
            result["error"] = "Arquivo PDF excede o limite de 10 MB."
            return result
        result["raw_text"] = _extract_pdf_text(file_bytes)

    if pasted_text and pasted_text.strip():
        existing = result.get("raw_text", "")
        result["raw_text"] = (existing + "\n" + pasted_text.strip()[:8000]).strip()

    if norm_url and not result.get("raw_text"):
        status_code, html_text, _ = _safe_http_get(
            norm_url,
            timeout=6,
            allowed_domain_suffixes=("linkedin.com",),
        )
        if status_code == 200 and html_text:
            soup = BeautifulSoup(html_text, "html.parser")
            title_meta = soup.find("meta", property="og:title")
            desc_meta = soup.find("meta", property="og:description")
            if title_meta and title_meta.get("content"):
                result["headline"] = title_meta["content"]
            if desc_meta and desc_meta.get("content"):
                result["summary"] = desc_meta["content"]

    if not result.get("languages") and result.get("raw_text"):
        result["languages"] = extract_languages_from_text(result["raw_text"])

    return result


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrai texto de um arquivo PDF usando pypdf/PyPDF2 se disponível ou fallback de streams."""
    if len(pdf_bytes) > _MAX_UPLOAD_FILE_BYTES:
        return ""
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            mod = __import__(mod_name)
            reader = mod.PdfReader(io.BytesIO(pdf_bytes))
            pages = [p.extract_text() or "" for p in reader.pages[:25]]
            text = "\n".join(pages).strip()
            if text:
                return text[:6000]
        except Exception:
            continue

    # Fallback leve: extrai strings legíveis entre parênteses em fluxos PDF descomprimidos
    import zlib

    extracted: List[str] = []
    for match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", pdf_bytes, re.DOTALL):
        chunk = match.group(1)
        try:
            decomp = zlib.decompress(chunk)
        except Exception:
            decomp = chunk
        for txt_match in re.finditer(rb"\(([^()]{2,200})\)", decomp):
            piece = txt_match.group(1).decode("latin-1", errors="ignore")
            if any(c.isalpha() for c in piece):
                extracted.append(piece)
    return " ".join(extracted)[:5000]


def extract_portfolio(portfolio_url: str = "") -> Dict[str, Any]:
    """Extrai projetos, bio, habilidades e metadados de uma página web de portfólio pessoal (com proteção anti-SSRF)."""
    if not portfolio_url or not portfolio_url.strip():
        return {}

    url = portfolio_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result: Dict[str, Any] = {"url": url}
    try:
        status_code, html_text, err_msg = _safe_http_get(url, timeout=10)
        if status_code != 200 or not html_text:
            result["error"] = err_msg or f"HTTP {status_code}"
            return result

        soup = BeautifulSoup(html_text, "html.parser")

        title = (soup.title.string or "").strip() if soup.title else ""
        desc = ""
        for meta_attr in ({"name": "description"}, {"property": "og:description"}):
            m = soup.find("meta", attrs=meta_attr)
            if m and m.get("content"):
                desc = m["content"].strip()
                break

        for tag in soup(["script", "style", "svg", "noscript", "iframe"]):
            tag.decompose()

        headings = [
            h.get_text(" ", strip=True)
            for h in soup.find_all(["h1", "h2", "h3"])
            if h.get_text(" ", strip=True)
        ][:15]

        body_text = soup.get_text(" ", strip=True)
        body_text = re.sub(r"\s+", " ", body_text).strip()[:3500]

        result.update(
            {
                "title": title,
                "description": desc,
                "headings": headings,
                "raw_text": body_text,
            }
        )
    except Exception as exc:
        result["error"] = f"Falha ao extrair portfólio ({type(exc).__name__})"

    return result



