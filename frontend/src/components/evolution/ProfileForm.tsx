import { type FormEvent, useState } from 'react';

import type { MarkerProfile, ProfileInput } from '../../api/evolution';
import { useSaveProfile } from '../../hooks/useEvolution';
import { frNumber, localToday, shortDate } from '../../utils/format';
import { Field } from '../Field';

type Key = 'waist_cm' | 'height_cm' | 'birth_year' | 'cap_db_m' | 'lsm_kpa';
type Values = Record<Key, string>;

const EMPTY: Values = {
  waist_cm: '',
  height_cm: '',
  birth_year: '',
  cap_db_m: '',
  lsm_kpa: '',
};

interface FieldSpec {
  key: Key;
  label: string;
  min: number;
  max: number;
  integer: boolean;
}

// Same bounds as the backend's ProfileIn validation.
const FIELDS: FieldSpec[] = [
  {
    key: 'waist_cm',
    label: 'Tour de taille (cm)',
    min: 40,
    max: 250,
    integer: false,
  },
  {
    key: 'height_cm',
    label: 'Taille (cm)',
    min: 100,
    max: 250,
    integer: false,
  },
  {
    key: 'birth_year',
    label: 'Année de naissance',
    min: 1900,
    max: 2100,
    integer: true,
  },
  {
    key: 'cap_db_m',
    label: 'FibroScan CAP (dB/m)',
    min: 100,
    max: 400,
    integer: false,
  },
  {
    key: 'lsm_kpa',
    label: 'FibroScan élasticité E (kPa)',
    min: 1.5,
    max: 75,
    integer: false,
  },
];

function parse(raw: string): number | undefined {
  const text = raw.trim().replace(',', '.');
  const value = Number(text);
  return text && Number.isFinite(value) ? value : undefined;
}

function outOfRange(spec: FieldSpec, raw: string): boolean {
  if (!raw.trim()) {
    return false;
  }
  const value = parse(raw);
  return (
    value === undefined ||
    value < spec.min ||
    value > spec.max ||
    (spec.integer && !Number.isInteger(value))
  );
}

/** French error for the first filled field outside its bounds, if any. */
function validate(values: Values): string | null {
  const bad = FIELDS.find((spec) => outOfRange(spec, values[spec.key]));
  if (!bad) {
    return null;
  }
  return `${bad.label} : valeur attendue entre ${bad.min} et ${bad.max}.`;
}

/** Only the filled fields are sent; null when nothing was entered. */
function toBody(values: Values, day: string): ProfileInput | null {
  const body: ProfileInput = {};
  for (const { key } of FIELDS) {
    const value = parse(values[key]);
    if (value !== undefined) {
      body[key] = value;
    }
  }
  if (Object.keys(body).length === 0) {
    return null;
  }
  return { ...body, date_key: day || localToday() };
}

function placeholder(profile: MarkerProfile | undefined, key: Key): string {
  const value = profile?.[key];
  if (value === null || value === undefined) {
    return '';
  }
  return key === 'birth_year' ? String(value) : frNumber(value);
}

interface InputsProps {
  values: Values;
  profile?: MarkerProfile;
  onChange: (key: Key, value: string) => void;
}

function ProfileInputs({ values, profile, onChange }: InputsProps) {
  return (
    <div className="profile-fields">
      {FIELDS.map((field) => (
        <div key={field.key} className="profile-field">
          <Field
            id={`profile-${field.key}`}
            label={field.label}
            value={values[field.key]}
            placeholder={placeholder(profile, field.key)}
            inputMode={field.integer ? 'numeric' : 'decimal'}
            onChange={(value) => onChange(field.key, value)}
          />
        </div>
      ))}
    </div>
  );
}

function ProfileFacts({ profile }: { profile?: MarkerProfile }) {
  if (!profile) {
    return null;
  }
  const waist = profile.waist_date
    ? `mesuré le ${shortDate(profile.waist_date)}`
    : 'jamais mesuré';
  const weight =
    typeof profile.weight_kg === 'number'
      ? `${frNumber(profile.weight_kg)} kg (dernière pesée)`
      : 'aucune pesée';
  return (
    <p className="muted profile-facts">
      Tour de taille : {waist} · Poids utilisé : {weight}
    </p>
  );
}

function SaveStatus({ error, saved }: { error?: string; saved: boolean }) {
  if (error) {
    return <span className="error">Erreur : {error}</span>;
  }
  return saved ? <span className="muted">Enregistré.</span> : null;
}

function useProfileForm() {
  const [values, setValues] = useState<Values>(EMPTY);
  const [day, setDay] = useState(localToday);
  const [invalid, setInvalid] = useState<string | null>(null);
  const mutation = useSaveProfile();
  const onChange = (key: Key, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const problem = validate(values);
    setInvalid(problem);
    const body = problem ? null : toBody(values, day);
    if (body) {
      mutation.mutate(body, { onSuccess: () => setValues(EMPTY) });
    }
  };
  const error = invalid ?? mutation.error?.message;
  return { values, onChange, submit, error, mutation, day, setDay };
}

export function ProfileForm({ profile }: { profile?: MarkerProfile }) {
  const form = useProfileForm();
  const { values, onChange, submit, error, mutation } = form;
  return (
    <form className="profile-form" onSubmit={submit} noValidate>
      <ProfileInputs values={values} profile={profile} onChange={onChange} />
      <div className="profile-field profile-date">
        <Field
          id="profile-date"
          label="Date de la mesure (FibroScan, tour de taille…)"
          type="date"
          value={form.day}
          onChange={form.setDay}
        />
      </div>
      <div className="profile-actions">
        <button className="btn" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Enregistrement…' : 'Enregistrer'}
        </button>
        <SaveStatus error={error} saved={mutation.isSuccess && !error} />
      </div>
      <ProfileFacts profile={profile} />
    </form>
  );
}
