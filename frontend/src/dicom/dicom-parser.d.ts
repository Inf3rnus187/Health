declare module 'dicom-parser' {
  export interface Element {
    dataOffset: number;
    length: number;
  }

  export interface DataSet {
    byteArray: Uint8Array;
    elements: Record<string, Element>;
    uint16(tag: string, index?: number): number | undefined;
    int16(tag: string, index?: number): number | undefined;
    string(tag: string, index?: number): string | undefined;
    intString(tag: string, index?: number): number | undefined;
    floatString(tag: string, index?: number): number | undefined;
  }

  export function parseDicom(byteArray: Uint8Array): DataSet;

  const dicomParser: { parseDicom: typeof parseDicom };
  export default dicomParser;
}
