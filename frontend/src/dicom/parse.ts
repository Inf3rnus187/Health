import dicomParser, { type DataSet, type Element } from 'dicom-parser';

export interface DicomImage {
  rows: number;
  cols: number;
  pixels: Int16Array | Uint16Array | Uint8Array;
  slope: number;
  intercept: number;
  invert: boolean;
  instance: number;
  meta: Record<string, string>;
}

export class UnsupportedDicom extends Error {}

const UNCOMPRESSED = new Set([
  '1.2.840.10008.1.2',
  '1.2.840.10008.1.2.1',
  '1.2.840.10008.1.2.2',
]);

const META_TAGS: readonly (readonly [string, string])[] = [
  ['x00100010', 'Patient'],
  ['x00080060', 'Modalité'],
  ['x00080020', 'Date'],
  ['x00081030', 'Étude'],
  ['x0008103e', 'Série'],
];

export function parse(buffer: ArrayBuffer): DicomImage {
  const dataSet = dicomParser.parseDicom(new Uint8Array(buffer));
  const syntax = dataSet.string('x00020010') ?? '1.2.840.10008.1.2';
  if (!UNCOMPRESSED.has(syntax)) {
    throw new UnsupportedDicom(describe(dataSet));
  }
  return build(dataSet, buffer, syntax === '1.2.840.10008.1.2.2');
}

function build(ds: DataSet, buffer: ArrayBuffer, be: boolean): DicomImage {
  const element = ds.elements['x7fe00010'];
  if (!element) {
    throw new UnsupportedDicom('Fichier DICOM sans données image.');
  }
  const bits = ds.uint16('x00280100') ?? 16;
  const signed = (ds.uint16('x00280103') ?? 0) === 1;
  return {
    rows: ds.uint16('x00280010') ?? 0,
    cols: ds.uint16('x00280011') ?? 0,
    pixels: readPixels(buffer, element, bits, signed, be),
    slope: firstFloat(ds, 'x00281053') ?? 1,
    intercept: firstFloat(ds, 'x00281052') ?? 0,
    invert: (ds.string('x00280004') ?? '') === 'MONOCHROME1',
    instance: ds.intString('x00200013') ?? 0,
    meta: readMeta(ds),
  };
}

function readPixels(
  buffer: ArrayBuffer,
  element: Element,
  bits: number,
  signed: boolean,
  be: boolean,
): Int16Array | Uint16Array | Uint8Array {
  const src = new Uint8Array(buffer, element.dataOffset, element.length);
  if (bits <= 8) {
    return new Uint8Array(src);
  }
  const count = element.length >> 1;
  const view = new DataView(src.buffer, src.byteOffset, element.length);
  const out = signed ? new Int16Array(count) : new Uint16Array(count);
  for (let i = 0; i < count; i += 1) {
    out[i] = signed ? view.getInt16(i * 2, !be) : view.getUint16(i * 2, !be);
  }
  return out;
}

function firstFloat(ds: DataSet, tag: string): number | null {
  const raw = ds.string(tag);
  if (!raw) {
    return null;
  }
  const value = Number.parseFloat(raw.split('\\')[0] ?? raw);
  return Number.isFinite(value) ? value : null;
}

function readMeta(ds: DataSet): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [tag, label] of META_TAGS) {
    const value = ds.string(tag);
    if (value) {
      out[label] = value;
    }
  }
  return out;
}

function describe(ds: DataSet): string {
  const modality = ds.string('x00080060') ?? 'image';
  return (
    `DICOM ${modality} compressé : aperçu non disponible dans la ` +
    'visionneuse intégrée (métadonnées lisibles).'
  );
}
